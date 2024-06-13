'''https://habr.com/ru/companies/okkamgroup/articles/509204/'''
from typing import List, Union
import faiss
import numpy as np
from config import FAISSConfig
import os
import shutil
from pathlib import Path


class FAISS:
    def __init__(self, parameters: FAISSConfig):
        self.parameters: FAISSConfig = parameters
        self.index = faiss.index_factory(self.parameters.vector_dim, f"IVF{int(self.parameters.num_clusters)},PQ64", faiss.METRIC_L2)

        self._cur_vectors = np.empty((0, self.parameters.vector_dim))
        self._cur_vectors_ind = np.array([], dtype=np.int8)
        self._cur_ind = 0
        self._cur_num_block = 0
        self.ntotal = None
        # if self.parameters.overwriting_indexes and os.path.exists(self.parameters.path_to_index):
        #     shutil.rmtree(self.parameters.path_to_index)

    def training(self, train_vectors: np.array):
        self.index.train(train_vectors)
        self._save_index(os.path.join(self.parameters.path_to_index, self.parameters.trained_index))
        assert self.index.is_trained

    def _save_index(self, path_to_save: str):
        path = Path(path_to_save)
        if os.path.isdir(path):
            os.makedirs(path_to_save, exist_ok=True)
        else:
            os.makedirs(path.parent, exist_ok=True)

        faiss.write_index(self.index, path_to_save)

    def _create_block(self):
        '''Функция для создания блока индекса'''
        os.makedirs(self.parameters.path_to_block_index, exist_ok=True)

        if self._cur_vectors.shape[0] == 0:
            return

        index = faiss.read_index(os.path.join(self.parameters.path_to_index, self.parameters.trained_index))

        index.add_with_ids(self._cur_vectors, self._cur_vectors_ind)
        faiss.write_index(index,
                          os.path.join(self.parameters.path_to_block_index, f"block_{self._cur_num_block}.index"))

        # Обновление информации
        self._cur_num_block += 1
        self._cur_vectors = np.empty((0, self.parameters.vector_dim))
        self._cur_vectors_ind = np.array([])

    def add(self, data: np.array):
        shape = data.shape
        if len(shape) == 1:
            data = [data]
        indexes = []
        for item in data:
            if len(self._cur_vectors) == self.parameters.block_size:
                self._create_block()

            self._cur_vectors = np.vstack([self._cur_vectors, item])
            self._cur_vectors_ind = np.append(self._cur_vectors_ind, self._cur_ind)

            indexes.append(self._cur_ind)
            self._cur_ind += 1
        return indexes

    def _merge_block(self):
        final_index = faiss.read_index(os.path.join(self.parameters.path_to_index, self.parameters.trained_index))
        # ivfs = []
        for num_block in range(self._cur_num_block):
            block_index = faiss.read_index(
                os.path.join(self.parameters.path_to_block_index, f"block_{num_block}.index"))
            # ivfs.append(block_index.invlists)
            final_index.merge_from(block_index, num_block)
            block_index.own_invlists = False

        final_index.ntotal = sum(
            block_index.ntotal for block_index in
            [faiss.read_index(os.path.join(self.parameters.path_to_block_index, f"block_{num_block}.index"))
             for num_block in range(self._cur_num_block)])
        return final_index

    def save(self):
        self._create_block()
        self.index = self._merge_block()
        self._save_index(os.path.join(self.parameters.path_to_index, self.parameters.name_index))

    def load(self):
        self.index = faiss.read_index(os.path.join(self.parameters.path_to_index, self.parameters.name_index))
        self.ntotal = self.index.ntotal

    def search(self, query_vectors: np.array, k: int):
        distances, indices = self.index.search(query_vectors, k)
        return distances, indices
#
#
# if __name__ == "__main__":
#     faiss_config = FaissConfig()
#     d = faiss_config.vector_dim
#
#     db_faiss = Faiss(faiss_config)
#     # db_faiss.load()
#     # query_vectors = np.random.random((1, d)).astype('float32')
#     # distances, indices = db_faiss.search(query_vectors, k=10)
#     # print("Индексы ближайших соседей для каждого запроса:")
#     # print(indices)
#     #
#     # print("Дистанции до ближайших соседей для каждого запроса:")
#     # print(distances)
#
#     train_vectors = np.random.random((10 ** 4, d)).astype(
#         'float32')  # предварительно сформированный датасет для обучения
#     db_faiss.training(train_vectors)
#
#     # vectors = np.random.random((10 ** 4, d)).astype(
#     #     'float32')  # предварительно сформированный датасет для обучения
#     db_faiss.add(train_vectors)
#     db_faiss.save()
#
#     # db_faiss.load()
#     query_vectors = np.random.random((1, d)).astype('float32')
#     distances, indices = db_faiss.search(train_vectors[:3], k=10)
#     print("Индексы ближайших соседей для каждого запроса:")
#     print(indices)
#
#     print("Дистанции до ближайших соседей для каждого запроса:")
#     print(distances)
#
#     # d, i = db_faiss.frange_search(train_vectors[0], 100)
#     # print(i)
