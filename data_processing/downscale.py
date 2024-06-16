import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def save_raster_with_new_pixel_size_sync(input_path, output_path, new_pixel_size):
    """
    Сохраняет растровое изображение с новым размером пикселя.

    Этот метод читает растровое изображение из указанного пути, изменяет размер пикселей в соответствии с новыми
    размерами, указанными в `new_pixel_size`, и сохраняет результат в новый файл.

    Параметры:
    ----------
    input_path : str
        Путь к входному растровому файлу.
    output_path : str
        Путь к выходному растровому файлу.
    new_pixel_size : tuple
        Новый размер пикселя в формате (ширина, высота).

    Возвращает:
    -----------
    None
    """
    with rasterio.open(input_path) as dataset:
        # Создаем новую аффинную трансформацию с учетом нового размера пикселя
        new_transform = Affine(new_pixel_size[0], 0, dataset.transform.c,
                               0, -new_pixel_size[1], dataset.transform.f)

        # Вычисляем новые размеры изображения
        new_width = int(dataset.width * (dataset.transform.a / new_pixel_size[0]))
        new_height = int(dataset.height * (-dataset.transform.e / new_pixel_size[1]))

        # Обновляем метаданные для нового изображения
        new_meta = dataset.meta.copy()
        new_meta.update({
            'transform': new_transform,
            'width': new_width,
            'height': new_height,
            'driver': 'GTiff',
            'crs': dataset.crs
        })

        # Считываем данные с измененным размером пикселей
        data = dataset.read(
            out_shape=(
                dataset.count,
                new_height,
                new_width
            ),
            resampling=Resampling.bilinear
        )

        # Сохраняем данные в новый файл с обновленными метаданными
        with rasterio.open(output_path, 'w', **new_meta) as dest:
            dest.write(data)

    logging.info(f"Saved raster with new pixel size to {output_path}")


async def save_raster_with_new_pixel_size(input_path, output_path, new_pixel_size, executor):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, save_raster_with_new_pixel_size_sync, input_path, output_path, new_pixel_size)


async def downscale(input_dir, output_dir, resolutions, executor):
    """
    Асинхронно уменьшает масштаб растровых изображений в указанной директории.

    Этот метод проходит по всем файлам в указанной директории, находит все файлы с расширением '.tif', сохраняет их копии в поддиректории 'original' и создает уменьшенные копии с различными разрешениями, которые сохраняются в указанной выходной директории.

    Параметры:
    ----------
    input_dir : str
        Путь к директории, содержащей входные файлы.
    output_dir : str
        Путь к директории, куда будут сохранены уменьшенные копии файлов.
    resolutions : list of tuple
        Список разрешений в формате (ширина, высота), к которым нужно привести изображения.
    executor : concurrent.futures.Executor
        Экзекутор для выполнения асинхронных задач.

    Возвращает:
    -----------
    None
    """
    tasks = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.tif'):
                input_path = os.path.join(root, file)
                filename = os.path.basename(input_path)
                base_name = os.path.splitext(filename)[0]

                # Создаем директорию для оригинальных файлов, если она не существует
                original_dir = os.path.join(output_dir, 'original')
                os.makedirs(original_dir, exist_ok=True)

                # Путь для сохранения оригинального файла
                original_output_path = os.path.join(original_dir, filename)
                # Копируем оригинальный файл в новую директорию
                with rasterio.open(input_path) as src:
                    with rasterio.open(original_output_path, 'w', **src.meta) as dest:
                        dest.write(src.read())

                logging.info(f"Copied original raster to {original_output_path}")

                # Создаем уменьшенные копии для каждого разрешения
                for res in resolutions:
                    downscale_dir = os.path.join(output_dir, 'downscale', f'{base_name}_downscale')
                    os.makedirs(downscale_dir, exist_ok=True)
                    output_path = os.path.join(downscale_dir, f'{base_name}_downscale_{res[0]}x{res[1]}.tif')
                    tasks.append(save_raster_with_new_pixel_size(input_path, output_path, res, executor))

    # Ожидаем завершения всех задач
    await asyncio.gather(*tasks)
    logging.info(f"Downscale completed for all rasters in {input_dir}")


if __name__ == "__main__":
    # Запрашиваем путь к корневой директории набора данных
    # print('Enter the path to the root directory for the dataset:')
    # input_path_root_dataset = input().strip()
    INPUT_PATH_ROOT_DATASET = os.getenv("INPUT_PATH_ROOT_DATASET")
    logging.info(f"Path to the root directory for the dataset: {INPUT_PATH_ROOT_DATASET}")

    # Запрашиваем путь к директории для сохранения уменьшенных изображений
    # print('Enter the path to the directory for saving downscaled images:')
    # output_dir = input().strip()

    OUTPUT_DIR = os.getenv("OUTPUT_DIR")
    logging.info(f"Path to the directory for saving downscaled images: {OUTPUT_DIR}")

    # Параметры разрешений для уменьшения масштаба
    resolutions = [
        (50, 50), (50, 60), (50, 70), (50, 80),
        (60, 50), (60, 60), (60, 70), (60, 80),
        (70, 50), (70, 60), (70, 70), (70, 80),
        (80, 50), (80, 60), (80, 70), (80, 80)
    ]

    # Создаем экзекутор с количеством рабочих потоков, равным количеству ядер процессора
    executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    # Запускаем асинхронную функцию downscale
    asyncio.run(downscale(INPUT_PATH_ROOT_DATASET, OUTPUT_DIR, resolutions, executor))
