'''Данный файл содержит код для разделения подложки на каналы и их преобразование к пространственному расширения 70м'''
import subprocess
import os

PATH_TO_DATA = f'{os.getcwd()}/inputs'
channels = [1, 2, 3]  # извлекаемые каналы (4 канала R, G, B, Nir) Каналы нумеруются с 1


def extract_channels(input_file, output_file):
    '''
    Функция для извлечения каналов из изображения

    :param input_file:
    :param output_file:
    :return:
    '''

    channel_string = ' '.join([f'-b {channel}' for channel in channels])
    command = f'docker run -v {PATH_TO_DATA}:/data ghcr.io/osgeo/gdal:alpine-normal-latest gdal_translate {channel_string} ' \
              f'-scale 0 4096 0 255 -ot Byte data/{input_file} data/{output_file}'

    # Запускаем команду в системном шелле
    subprocess.call(command, shell=True)


def resampling(input_file, output_file):
    # command = f'docker run -v {PATH_TO_DATA}:/data ghcr.io/osgeo/gdal:alpine-normal-latest gdalwarp -b 1 -b 2 -b 3 -overwrite -tr 50 50 -r bilinear data/{input_file} data/{output_file}'
    command = f'docker run -v {PATH_TO_DATA}:/data ghcr.io/osgeo/gdal:alpine-normal-latest gdalwarp -overwrite -tr 50 50 -r bilinear data/{input_file} data/{output_file}'

    # Запускаем команду в системном шелле
    subprocess.call(command, shell=True)




# Пример использования
input_path = 'layout_2021-06-15.tif'
output_path = 'output_layout.tif'

if __name__ == "__main__":
    # extract_channels(inpath, output_path)
    # resampling("LC08_L2SP_131015_20210729_20210804_02_T1_SR_B4.tif", '70m.tif')
    for ind, output_path in enumerate([f'bound_1.tif', 'bound_2.tif', 'bound_3.tif']):
        resampling(output_path, f'70m_{ind}.tif')
    # extract_bands(output_path)
