'''Данный скрипт содержит код для преобразования crop в 3-х канальные изображения'''
import os
from pathlib import Path
import rasterio
import numpy as np
import logging
from tqdm import tqdm
import cv2 as cv
from PIL import Image

logger = logging.getLogger(__name__)

PATH_TO_IMAGES = f'{os.getcwd()}/data/18. Sitronics/1_20'
PATH_TO_OUTPUT_DIR = 'output_crop'
MAX_PIXEL_VALUE = 4096  # Max. pixel value, used to normalize the image
BANDS = [1, 2, 3]


def convert_tif2img(path, bands):
    img = rasterio.open(path).read(bands).transpose((1, 2, 0))

    def normalize(image):
        # max_value = 4096
        image = np.log1p(image.astype(np.float32))
        min_value = np.min(image)
        max_value = np.max(image)
        # линейное преобразование для нормирования пикселей
        image = ((image - min_value) / (max_value - min_value)) * 255

        return image.astype(np.uint8)

    image = Image.fromarray(normalize(img))
    red, green, blue = image.split()

    image = Image.merge('RGB', (blue, green, red))
    return image


# def read_image(path, bands):
#     img = rasterio.open(path).read(bands).transpose((1, 2, 0))
#     # img = np.float32(img) / MAX_PIXEL_VALUE
#
#     return img


# def normalize(image):
#     min_value = np.min(image)
#     max_value = np.max(image)
#     # max_value = 4096
#     image_data = np.log1p(image.astype(np.float32))
#     # линейное преобразование для нормирования пикселей
#     normalized_image_data = ((image_data - min_value) / (max_value - min_value)) * 255
#
#     return normalized_image_data.astype(np.uint8)


# def save_image(img, output_file, metadata):
#     with rasterio.open(output_file, 'w', **metadata) as dst:
#         dst.write(img)


if __name__ == "__main__":
    logger.info(f'Каталог для сохранения преобразованных кропов {PATH_TO_OUTPUT_DIR}')
    os.makedirs(PATH_TO_OUTPUT_DIR, exist_ok=True)
    for name_file in tqdm(os.listdir(PATH_TO_IMAGES), desc='Преобразование кропов', ncols=180):
        path_to_img = Path(os.path.join(PATH_TO_IMAGES, name_file))

        img = convert_tif2img(path_to_img, BANDS)
        img.save(os.path.join(PATH_TO_OUTPUT_DIR, path_to_img.stem + '.png'))
