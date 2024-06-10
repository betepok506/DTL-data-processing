import os
import random
import rasterio
import csv
import logging
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_image(image_path, output_dir, relative_path, min_broken_pixels, max_broken_pixels):
    """
    Обрабатывает изображение, генерируя битые пиксели и сохраняет результат с сохранением исходной структуры каталогов.

    Args:
        image_path (str): Путь к исходному изображению.
        output_dir (Path): Корневая папка для сохранения обработанных изображений.
        relative_path (Path): Относительный путь для сохранения изображения.
        min_broken_pixels (int): Минимальное количество битых пикселей.
        max_broken_pixels (int): Максимальное количество битых пикселей.

    Returns:
        list: Список строк для записи в CSV файл.
    """
    csv_rows = []
    original_file_name = Path(image_path).stem  # Исходное имя файла без расширения

    logging.info(f"Processing image: {image_path}")
    try:
        with rasterio.open(image_path) as src:
            image = src.read()  # Читаем данные изображения
            rows, cols = image.shape[1], image.shape[2]
            num_broken_pixels = random.randint(min_broken_pixels,
                                               max_broken_pixels)  # Случайное количество битых пикселей

            for _ in range(num_broken_pixels):
                row = random.randint(0, rows - 1)  # Случайный номер строки
                col = random.randint(0, cols - 1)  # Случайный номер столбца
                channel = random.randint(0, image.shape[0] - 1)  # Случайный канал
                original_value = image[channel, row, col]  # Исходное значение пикселя
                broken_value = generate_broken_value(original_value, image.dtype)  # Генерация битого значения
                image[channel, row, col] = broken_value  # Замена значения пикселя

                # Запись информации о битом пикселе в список
                csv_rows.append(
                    [f"{original_file_name}_broken_pixels.tif", f"{original_file_name}.tif", row, col, channel, broken_value,
                     original_value])

            meta = src.meta  # Метаданные изображения

            output_file_path = output_dir / relative_path.with_name(
                f"{original_file_name}_broken_pixels.tif")  # Путь для сохранения обработанного изображения
            output_file_path.parent.mkdir(parents=True, exist_ok=True)  # Создание необходимых директорий

            # Сохранение обработанного изображения
            with rasterio.open(output_file_path, 'w', **meta) as dst:
                dst.write(image)

        logging.info(f"Finished processing image: {image_path}")
    except Exception as e:
        logging.error(f"Error processing image {image_path}: {e}")

    return csv_rows


def generate_broken_value(original_value, dtype):
    """
    Генерирует значение битого пикселя в зависимости от заданного режима.

    Args:
        original_value (int): Исходное значение пикселя.
        dtype (dtype): Тип данных пикселя.

    Returns:
        int: Значение битого пикселя.
    """
    # Выбор режима генерации битого пикселя
    mode = random.choice(['zero', 'underexposed', 'overexposed'])
    if mode == 'zero':
        return 0  # Установка значения в 0
    elif mode == 'underexposed':
        broken_value = int(original_value * random.uniform(0, 0.15))  # Значительное недосвечивание
    elif mode == 'overexposed':
        broken_value = int(original_value * random.uniform(5, 10))  # Значительное пересвечивание

    # Убедиться, что значение битого пикселя находится в пределах допустимого диапазона для данного типа данных
    if np.issubdtype(dtype, np.integer):
        info = np.iinfo(dtype)
        broken_value = np.clip(broken_value, info.min, info.max)  # Ограничение значений для целочисленных данных
    elif np.issubdtype(dtype, np.floating):
        info = np.finfo(dtype)
        broken_value = np.clip(broken_value, info.min, info.max)  # Ограничение значений для чисел с плавающей запятой

    return broken_value


async def process_directory(input_dir, output_dir, min_broken_pixels, max_broken_pixels, csv_writer):
    """
    Асинхронно обрабатывает все изображения в заданной директории, генерируя битые пиксели.

    Args:
        input_dir (str): Путь к папке с исходными изображениями.
        output_dir (Path): Корневая папка для сохранения обработанных изображений.
        min_broken_pixels (int): Минимальное количество битых пикселей.
        max_broken_pixels (int): Максимальное количество битых пикселей.
        csv_writer (csv.writer): Объект для записи данных в CSV файл.
    """
    tasks = []  # Список задач для выполнения
    loop = asyncio.get_event_loop()  # Получение текущего цикла событий
    with ThreadPoolExecutor() as executor:
        # Рекурсивно обходим директорию
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.tif'):  # Проверка формата файла
                    image_path = os.path.join(root, file)
                    relative_path = Path(image_path).relative_to(input_dir)  # Относительный путь файла
                    # Создание задачи для обработки изображения
                    tasks.append(loop.run_in_executor(
                        executor, process_image, image_path, output_dir, relative_path, min_broken_pixels,
                        max_broken_pixels
                    ))
        results = await asyncio.gather(*tasks)  # Ожидание завершения всех задач

    # Запись результатов в CSV файл
    for csv_rows in results:
        for row in csv_rows:
            csv_writer.writerow(row)


def main():
    # Запросы на английском языке
    input_dir = input("Enter the path to the folder with images in TIFF format: ")
    output_dir = input("Enter the path where the images should be saved: ")
    min_broken_pixels = int(input("Enter the minimum number of broken pixels: "))
    max_broken_pixels = int(input("Enter the maximum number of broken pixels: "))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)  # Создание выходной директории, если она не существует

    csv_file_path = output_dir / 'broken_pixels_log.csv'
    # Открытие CSV файла для записи логов
    with open(csv_file_path, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=';')
        csv_writer.writerow(
            ['generated_file_name', 'original_file_name', 'row', 'col', 'channel', 'broken_value', 'original_value'])

        logging.info("Starting image processing...")
        asyncio.run(process_directory(input_dir, output_dir, min_broken_pixels, max_broken_pixels,
                                      csv_writer))  # Запуск асинхронной обработки
        logging.info("Image processing completed.")


if __name__ == "__main__":
    main()
