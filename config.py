'''Данный скрипт содержит файлы конфигурации проекта'''
import os


class FAISSConfig:
    '''Данный класс содержит параметры конфигурации для работы с FAISS'''
    path_to_index: str = './data_faiss'  # Путь до папки, где хранятся индексы
    path_to_block_index: str = f'{path_to_index}/block'  # Путь до папки, содержищей блоки индекса
    name_index: str = 'faiss_index.index'  # Название файла, содержащего индекс
    trained_index: str = 'trained_index.index'  # Название файла, содержащего индекс для тренировки

    vector_dim: int = 128  # Размер вектора
    num_clusters: int = 512  # Количество векторов
    block_size: int = 1024  # Количество векторов в одном блоке

    overwriting_indexes = False  # True если удалять ранее созданный индекс


class ExtractingFeaturesConfig:
    '''Данный класс содержит параметры конфигурации для pipeline извлечения фиф из изображений датасета'''
    path_to_data: str = f'./data/crop'  # Путь до нарезанного набора данных (До папки crop)
    server_port: str = 8000
    server_uri: str = 'localhost'
    server_url: str = f'http://{server_uri}:{server_port}'
    block_size: int = 512 # Количество элементов layout, которые будет отправляться за раз на сервер
