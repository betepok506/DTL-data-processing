'''Данный модель содержит скрипт для преобразования сгенерированных слоев подложки в вектор и запись их в базу данных'''
from typing import List, Dict
from faiss_search.faiss_interface import FAISS
import os
from config import ExtractingFeaturesConfig, FAISSConfig
from PIL import Image
import numpy as np
from utils.api_requests import send_request
from utils.api_requests import ApiClient
import rasterio
from shapely.geometry import Polygon
from pyproj import Transformer
from tqdm import tqdm
from utils.transform import transform_polygon


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


def pipeline_extracting_features():
    faiss_config = FAISSConfig()
    d = faiss_config.vector_dim
    extracting_features_config = ExtractingFeaturesConfig()
    api_client = ApiClient(extracting_features_config.server_url)
    train_vector = np.empty((0, d))
    data = []
    # Объявление faiss
    db_faiss = FAISS(faiss_config)
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
                feature_vector = np.random.random(d).astype('float32')
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
        break
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
    pipeline_extracting_features()
