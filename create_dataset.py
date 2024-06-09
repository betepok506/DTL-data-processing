"""Данный модуль содержит код формирования датасета обучения нейронной сети"""
import pandas
from tqdm import tqdm
import os
from config import CreateDatasetConfig
import shutil
from pathlib import Path
from utils.convert_crop import convert_tif2img

if __name__ == "__main__":
    dataset_config = CreateDatasetConfig()
    ind_folder = 0
    shutil.rmtree(dataset_config.path_to_save_data)
    progress_bars = []
    progress_bars.append(tqdm(total=len(os.listdir(dataset_config.path_to_data)),
                              desc='Итерация по кропам',
                              position=0,
                              ncols=180))
    for folder_crop in os.listdir(dataset_config.path_to_data):
        # print(f'Cur folder: {folder_crop}')
        path_to_folder_crop = os.path.join(dataset_config.path_to_data, folder_crop)
        layouts_name = [item for item in os.listdir(path_to_folder_crop)]
        # print(f'Layout : {layouts_name}')
        cur_layout = layouts_name[0]

        progress_bars.append(tqdm(total=len(os.listdir(os.path.join(path_to_folder_crop, cur_layout))),
                                  desc='Итерация по файлам',
                                  position=1,
                                  leave=False,
                                  ncols=100))
        for filename in os.listdir(os.path.join(path_to_folder_crop, cur_layout)):
            # Получаем индексы изображения
            i_j = filename.replace(f'{cur_layout}_256x256_', '').replace('.tif', '').split('_')
            cur_save_folder = os.path.join(dataset_config.path_to_save_data, f'{ind_folder}')
            os.makedirs(cur_save_folder)
            for layout in layouts_name:
                path_to_file = os.path.join(path_to_folder_crop, layout, f'{layout}_256x256_{i_j[0]}_{i_j[1]}.tif')
                path_to_save_file = os.path.join(cur_save_folder,
                                                 f'{folder_crop}_{layout}_256x256_{i_j[0]}_{i_j[1]}.png')
                # shutil.copy(path_to_file, path_to_save_file)
                img = convert_tif2img(path_to_file, (1,2,3))
                # path_to_save_file = Path(path_to_save_file)
                img.save(path_to_save_file)
                progress_bars[1].update(1)

            ind_folder += 1

        progress_bars[0].update(1)
        progress_bars[1].close()
        progress_bars.pop(1)
    progress_bars[0].close()