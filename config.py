'''Данный скрипт содержит файлы конфигурации проекта'''
import os
from typing import List


class FAISSConfig:
    '''Данный класс содержит параметры конфигурации для работы с FAISS'''
    path_to_index: str = '/data_faiss'  # Путь до папки, где хранятся индексы
    path_to_block_index: str = f'{path_to_index}/block'  # Путь до папки, содержищей блоки индекса
    name_index: str = 'faiss_index.index'  # Название файла, содержащего индекс
    trained_index: str = 'trained_index.index'  # Название файла, содержащего индекс для тренировки

    vector_dim: int = 128  # Размер вектора
    num_clusters: int = 128  # Количество векторов
    block_size: int = 1024  # Количество векторов в одном блоке

    overwriting_indexes = False  # True если удалять ранее созданный индекс


class ExtractingFeaturesConfig:
    '''Данный класс содержит параметры конфигурации для pipeline извлечения фиф из изображений датасета'''
    path_to_data: str = f'./data/crop'  # Путь до нарезанного набора данных (До папки crop)
    server_port: str = 8000
    server_uri: str = 'aerial-photography-backend'
    # server_uri: str = 'localhost'
    server_url: str = f'http://{server_uri}:{server_port}'
    folder_to_use: List[str] = ['crop_50x50', 'crop_50x60', 'crop_50x70', 'crop_50x80',
                                'crop_60x50', 'crop_60x60', 'crop_60x70', 'crop_60x80',
                                'crop_70x50', 'crop_70x60', 'crop_70x70', 'crop_70x80',
                                'crop_80x50', 'crop_80x60', 'crop_80x70', 'crop_80x80']
    use_hog: bool = False
    block_size: int = 512  # Количество элементов layout, которые будет отправляться за раз на сервер
    load_prepared_vectors: bool = True
    path_to_prepared_vectors: str = '/data/prepared_vectors.npy'
    path_to_prepared_vectors_data: str = '/data/prepared_vectors_data.json'


class CreateDatasetConfig:
    path_to_data: str = './data/crop'
    path_to_save_data: str = './data/dataset'
