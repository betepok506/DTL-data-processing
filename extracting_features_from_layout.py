'''Данный модель содержит скрипт для преобразования сгенерированных слоев подложки в вектор и запись их в базу данных'''
from typing import List, Dict
from faiss_search.faiss_interface import FAISS
import os
from config import ExtractingFeaturesConfig, FAISSConfig
from PIL import Image
import numpy as np
from utils.convert_crop import convert_tif2img
from utils.api_requests import send_request
from utils.api_requests import ApiClient
import rasterio
from shapely.geometry import Polygon
from pyproj import Transformer
from tqdm import tqdm
from utils.transform import transform_polygon
import torch
import argparse
import json
from dtl_siamese_network import SiameseNet, TorhModelFeatureExtraction, ResNet
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
        crs = dataset.crs
        # Получение границ изображения в координатах пикселей
        width = dataset.width
        height = dataset.height

        # Координаты углов в пикселях
        pixel_corners = [
            (0, 0),  # Верхний левый угол
            (width, 0),  # Верхний правый угол
            (width, height),  # Нижний правый угол
            (0, height)  # Нижний левый угол
        ]

        # Преобразование координат пикселей в географические координаты
        geo_corners = [rasterio.transform.xy(transform, y, x) for x, y in pixel_corners]
        transformer = Transformer.from_crs(crs, "EPSG:32637", always_xy=True)
        latlon_corners = [transformer.transform(x, y) for x, y in geo_corners]

        # Создание полигона
        polygon = Polygon(latlon_corners)
        # transformed_polygon = transform_polygon(polygon, "EPSG:32637", "EPSG:4326")
        # Создание полигона
        # polygon = Polygon(geo_corners)

        # # Получение границ изображения
        # bounds = dataset.bounds
        #
        # # Координаты углов
        # corners = [
        #     (bounds.left, bounds.top),  # Верхний левый угол
        #     (bounds.right, bounds.top),  # Верхний правый угол
        #     (bounds.right, bounds.bottom),  # Нижний правый угол
        #     (bounds.left, bounds.bottom),  # Нижний левый угол
        #     (bounds.left, bounds.top)  # Замыкаем полигон, возвращаемся в начало
        # ]
        #
        # # Создание полигона
        # polygon = Polygon(corners)

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
    extracting_features_config = ExtractingFeaturesConfig()

    api_client = ApiClient(extracting_features_config.server_url)

    train_vector = np.empty((0, d))
    data = []
    # Объявление faiss
    db_faiss = FAISS(faiss_config)
    embedding_net = ResNet()
    # embedding_net = TorhModelFeatureExtraction(name=name_model)
    model = SiameseNet(embedding_net)
    print(f'Имя модели: {name_model}')
    # model = torch.load(PATH_TO_MODEL_WEIGHT)
    # checkpoint = torch.load(PATH_TO_MODEL_WEIGHT)
    model.load_state_dict(torch.load(path_to_weight))
    model.to(device)
    # img = Image.open(path_to_file)
    if not extracting_features_config.load_prepared_vectors and os.path.exists(extracting_features_config.path_to_prepared_vectors):
        print('Удаляю предварительно подготовленные вектора')
        os.remove(extracting_features_config.path_to_prepared_vectors)

    if not extracting_features_config.load_prepared_vectors and os.path.exists(extracting_features_config.path_to_prepared_vectors_data):
        print('Удаляю данные предварительно подготовленных векторов...')
        os.remove(extracting_features_config.path_to_prepared_vectors_data)

    if not extracting_features_config.load_prepared_vectors or not os.path.exists(extracting_features_config.path_to_prepared_vectors):

        for folder_crop in os.listdir(ExtractingFeaturesConfig.path_to_data):
            path_to_folder_crop = os.path.join(ExtractingFeaturesConfig.path_to_data, folder_crop)

            for folder_layout_crop in os.listdir(path_to_folder_crop):
                print(folder_layout_crop)
                path_to_layout_crop = os.path.join(path_to_folder_crop, folder_layout_crop)

                for filename in tqdm(os.listdir(path_to_layout_crop),
                                     desc=f'Перебираю файлы в папке {folder_crop}/{folder_layout_crop}',
                                     ncols=180):
                    path_to_filename = os.path.join(path_to_layout_crop, filename)
                    image, polygon = read_image(path_to_filename)

                    # Псевдо вектор признаков
                    # feature_vector = np.random.random(d).astype('float32')
                    image = normalize(image[:3].transpose((1, 2, 0)))
                    # image = convert_tif2img(path_to_filename, (1,2,3))
                    feature_vector = model.predict(image, device=device)
                    feature_vector = feature_vector.cpu().detach().numpy()

                    # Добавление вектора в базу FAISS
                    # index = db_faiss.add(feature_vector)[0]
                    train_vector = np.vstack((train_vector, feature_vector))

                    dim_space_x, dim_space_y = folder_crop.replace("crop_", "").split("x")
                    data.append({
                        'faiss_id': None,
                        "polygon_coordinates": str(polygon),
                        "layout_name": folder_layout_crop,
                        "dim_space_x": int(dim_space_x),
                        "dim_space_y": int(dim_space_y),
                        "filename": filename
                    })

                    # # Отправляем данные в базу
                    # if len(data) >= faiss_config.block_size:
                    #     response = send_data_for_server(api_client, data)
                    #
                    #     if not 200 <= response.status_code < 300:
                    #         raise "Ошибка при добавлении слоя в БД"
                    #     print(response.json())
                    # predict = model.predict(image)
            break

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

    print(f'Количество векторов для обучения FAISS {len(train_vector.shape)}')
    print('Обучение FAISS...')
    db_faiss.training(train_vectors=train_vector)
    print("Обучение заверешно...")

    for start_block in range(0, train_vector.shape[0], faiss_config.block_size):
        # print(f'start {start_block} end {start_block + faiss_config.block_size}')
        index = db_faiss.add(train_vector[start_block: start_block + faiss_config.block_size])
        for ind_data, ind_vec in zip(range(start_block, start_block + faiss_config.block_size), index):
            data[ind_data]['faiss_id'] = ind_vec

        response = send_data_for_server(api_client, data[start_block: start_block + faiss_config.block_size])

        if not 200 <= response.status_code < 300:
            raise "Ошибка при добавлении слоя в БД"
        # print(response.json())


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="")
    # parser.add_argument("--path_to_weight", help="")
    # parser.add_argument("--name_model", help="")
    # args = parser.parse_args()
    path_to_weight = os.getenv('PATH_TO_WEIGHT')
    name_model = os.getenv('NAME_MODEL')
    pipeline_extracting_features(path_to_weight, name_model)
