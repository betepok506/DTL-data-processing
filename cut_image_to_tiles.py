'''Данный скрипт содержит код для нарезки подложки на плитки по сетке'''
import rasterio
from rasterio.windows import Window
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

PATH_TO_INPUT_FILE = 'D:\\projects_andrey\\datasets\\landsat8\\data\\output_8bit_131015_20210729_20210804.tif'
PATH_TO_OUTPUT_DIR = 'output_dir_tiles'
TILE_SIZE = 256


def split_image(input_path, output_dir, tile_size):
    '''
    Функция для нарезки изображения на плитки

    Parameters
    -------------
    input_path: `str`
        Путь до исходного нарезаемого изображения
    output_dir: `str`
        Путь до каталога куда будет сохранены нарезанные изображения
    tile_size: `int`
        Размер нарезаемых плиток
    '''
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with rasterio.open(input_path) as src:
        width = src.width
        height = src.height
        transform = src.transform

        for i in range(0, width, tile_size):
            for j in range(0, height, tile_size):
                logger.info(f"Обрабатываю прямоуголльник {i} {j} ")
                window = Window(i, j, tile_size, tile_size)
                transform_window = rasterio.windows.transform(window, transform)
                tile = src.read(window=window)

                # output_path = f"{output_prefix}_{i}_{j}.tiff"
                output_path = os.path.join(output_dir, f'tile_{i}_{j}.tiff')
                with rasterio.open(output_path, 'w', driver='GTiff',
                                   height=window.height,
                                   width=window.width,
                                   count=src.count,
                                   dtype=src.dtypes[0],
                                   crs=src.crs,
                                   transform=transform_window) as dst:
                    dst.write(tile)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logger.info(f"Обрабатываю снимок {PATH_TO_INPUT_FILE}")
    split_image(PATH_TO_INPUT_FILE, PATH_TO_OUTPUT_DIR, TILE_SIZE)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
