'''Данный модель содержит скрипт для преобразования сгенерированных слоев подложки в вектор и запись их в базу данных'''
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from typing import List, Dict
from faiss_search.faiss_interface import FAISS
from config import ExtractingFeaturesConfig, FAISSConfig
from PIL import Image
import numpy as np
from utils.api_requests import ApiClient
import rasterio
from shapely.geometry import Polygon
from tqdm import tqdm
from utils.transform import transform_polygon
import torch
import argparse
import json
from utils.convert_crop import convert_tif2img
from dtl_siamese_network import SiameseNet, TorhModelFeatureExtraction, ResNet, hog_feature_extraction, ResNet2
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PATH_TO_MODEL_WEIGHT = '/weights/checkpoint_efficientnet_b0.pth'


def read_image(path_to_image: str):
    '''Функция для чтения изображения и извлечения координат углов'''

    with rasterio.open(path_to_image) as dataset:
        # Чтение данных изображения
        image_data = dataset.read()

        # Получение трансформации изображения
        transform = dataset.transform
        upper_left = (transform[2], transform[5])  # координаты левого верхнего угла
        lower_right = (transform[2] + transform[0] * dataset.width,  # X координата правого нижнего угла
                       transform[5] + transform[4] * dataset.height)
        polygon = transform_polygon(Polygon([
            (upper_left[0], upper_left[1]),
            (lower_right[0], upper_left[1]),
            (lower_right[0], lower_right[1]),
            (upper_left[0], lower_right[1])
        ]),"EPSG:32637", "EPSG:4326" )

        return image_data, polygon


def send_data_for_server(api_client, data: List[Dict]):
    response = api_client.add_layer({'layers': data})
    return response


def normalize(image):
    # max_value = 4096
    image = np.log1p(image.astype(np.float32))
    min_value = np.min(image)
    max_value = np.max(image)
    # линейное преобразование для нормирования пикселей
    image = ((image - min_value) / (max_value - min_value)) * 255

    return image.astype(np.uint8)


def pipeline_extracting_features(path_to_weight, name_model):
    faiss_config = FAISSConfig()
    d = faiss_config.vector_dim
    logger.info(f'\t\t Количество кластеров: {faiss_config.num_clusters}')
    logger.info(f'\t\t Путь до модели: {path_to_weight}')

    extracting_features_config = ExtractingFeaturesConfig()

    api_client = ApiClient(extracting_features_config.server_url)

    train_vector = np.empty((0, d))
    data = []
    # Объявление faiss
    db_faiss = FAISS(faiss_config)
    embedding_net = ResNet2()

    model = SiameseNet(embedding_net)
    print(f'Имя модели: {name_model}')
    model.load_state_dict(torch.load(path_to_weight))
    model.eval()
    model.to(device)

    if not extracting_features_config.load_prepared_vectors and os.path.exists(extracting_features_config.path_to_prepared_vectors):
        print('Удаляю предварительно подготовленные вектора')
        os.remove(extracting_features_config.path_to_prepared_vectors)

    if not extracting_features_config.load_prepared_vectors and os.path.exists(extracting_features_config.path_to_prepared_vectors_data):
        print('Удаляю данные предварительно подготовленных векторов...')
        os.remove(extracting_features_config.path_to_prepared_vectors_data)

    if not extracting_features_config.load_prepared_vectors or not os.path.exists(extracting_features_config.path_to_prepared_vectors):

        for folder_crop in os.listdir(ExtractingFeaturesConfig.path_to_data):
            if folder_crop == 'crop_10x10':
                continue

            path_to_folder_crop = os.path.join(ExtractingFeaturesConfig.path_to_data, folder_crop)

            for folder_layout_crop in os.listdir(path_to_folder_crop):
                print(folder_layout_crop)
                path_to_layout_crop = os.path.join(path_to_folder_crop, folder_layout_crop)

                for filename in tqdm(os.listdir(path_to_layout_crop),
                                     desc=f'Перебираю файлы в папке {folder_crop}/{folder_layout_crop}',
                                     ncols=180):
                    path_to_filename = os.path.join(path_to_layout_crop, filename)
                    image, polygon = read_image(path_to_filename)

                    image = convert_tif2img(path_to_filename, (1,2,3))
                    with torch.no_grad():
                        feature_vector = model.predict(image, device=device)
                        feature_vector = feature_vector.cpu().detach().numpy()

                    try:
                        train_vector = np.vstack((train_vector, feature_vector))
                    except ValueError as e:
                        print(f'Произошла ошибка: {e}. Был неверно указан размер векторов и он автоматически исправлен. ')
                        train_vector = np.empty((0, feature_vector.shape[1]))
                        train_vector = np.vstack((train_vector, feature_vector))
                        faiss_config.vector_dim = feature_vector.shape[1]

                    dim_space_x, dim_space_y = folder_crop.replace("crop_", "").split("x")
                    data.append({
                        'faiss_id': None,
                        "polygon_coordinates": str(polygon),
                        "layout_name": folder_layout_crop.replace('_crop', ''),
                        "dim_space_x": int(dim_space_x),
                        "dim_space_y": int(dim_space_y),
                        "filename": filename
                    })


        print('Записываю вектора на диск')
        # Запись векторов признаков на диск
        np.save(extracting_features_config.path_to_prepared_vectors, train_vector)

        print('Записываю данные векторов на диск')
        # Запись данных векторов на диск
        with open(extracting_features_config.path_to_prepared_vectors_data, 'w') as f:
            json.dump(data, f)
    else:
        print('Загружаю предварительно полученные вектора...')
        # Загрузка веторов признаков
        train_vector = np.load(extracting_features_config.path_to_prepared_vectors)

        print('Загружаю предварительно полученные данные векторов...')
        # Загрузка данных векторов с диска
        with open(extracting_features_config.path_to_prepared_vectors_data, 'r') as f:
            data = json.load(f)

    print(f'Количество векторов для обучения FAISS {train_vector.shape}')
    print('Обучение FAISS...')
    print(f'Размер выборки для обучения: {train_vector.shape}')
    db_faiss.training(train_vectors=train_vector)
    print("Обучение заверешно...")

    for start_block in range(0, train_vector.shape[0], faiss_config.block_size):
        # print(f'start {start_block} end {start_block + faiss_config.block_size}')
        index = db_faiss.add(train_vector[start_block: start_block + faiss_config.block_size])
        for ind_data, ind_vec in zip(range(start_block, start_block + faiss_config.block_size), index):
            data[ind_data]['faiss_id'] = ind_vec
            data[ind_data]['layout_name'] = '_'.join(data[ind_data]['layout_name'].split('_')[:2])

        response = send_data_for_server(api_client, data[start_block: start_block + faiss_config.block_size])

        if not 200 <= response.status_code < 300:
            raise "Ошибка при добавлении слоя в БД"
        # print(response.json())
    print(f'Количество векторов в FAISS: {db_faiss.index.ntotal}')
    db_faiss.save()


if __name__ == "__main__":

    path_to_weight = os.getenv('PATH_TO_WEIGHT', './weights/resnet50_2_cosine_similarity.pth')
    name_model = os.getenv('NAME_MODEL', 'resnet50')
    pipeline_extracting_features(path_to_weight, name_model)
