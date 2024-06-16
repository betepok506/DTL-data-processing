import os
import asyncio
import rasterio
from rasterio.windows import Window
from concurrent.futures import ThreadPoolExecutor
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def crop_image_sync(input_path_layout, output_base_dir, step_multiplier):
    """
    Обрезает растровое изображение на основе заданного размера и шага.

    Этот метод читает растровое изображение из указанного пути, обрезает его на фрагменты заданного размера,
    и сохраняет их в указанной выходной директории.

    Параметры:
    ----------
    input_path_layout : str
        Путь к входному растровому файлу.
    output_base_dir : str
        Путь к базовой выходной директории.
    step_multiplier : float
        Множитель для шага обрезки изображения. Определяет степень перекрытия обрезков.

    Возвращает:
    -----------
    None
    """
    with rasterio.open(input_path_layout) as dataset:
        filename = os.path.basename(input_path_layout)
        base_name = os.path.splitext(filename)[0]
        pixel_size_x, pixel_size_y = dataset.res
        crop_size = 256
        step_size = int(crop_size * step_multiplier)  # Вычисляем шаг обрезки на основе множителя
        output_dir = os.path.join(output_base_dir, f'crop_{int(pixel_size_x)}x{int(pixel_size_y)}', f'{base_name}_crop')
        os.makedirs(output_dir, exist_ok=True)
        width, height = dataset.width, dataset.height
        num_iterations_x = (width - crop_size) // step_size + 1
        num_iterations_y = (height - crop_size) // step_size + 1

        for i in range(num_iterations_x):
            for j in range(num_iterations_y):
                x_offset = i * step_size
                y_offset = j * step_size
                window = Window(x_offset, y_offset, crop_size, crop_size)
                transform = dataset.window_transform(window)
                output_path = os.path.join(
                    output_dir,
                    f'{base_name}_crop_256x256_{i}_{j}.tif'
                )
                data = dataset.read(window=window)
                meta = dataset.meta.copy()
                meta.update({
                    'driver': 'GTiff',
                    'height': crop_size,
                    'width': crop_size,
                    'transform': transform
                })
                with rasterio.open(output_path, 'w', **meta) as dest:
                    dest.write(data)
                logging.info(f'Cropped image saved to {output_path}')  # Логируем сохранение обрезанного изображения

async def crop_image(input_path_layout, output_base_dir, step_multiplier, executor):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, crop_image_sync, input_path_layout, output_base_dir, step_multiplier)

async def process_directory(input_dir, output_base_dir, step_multiplier, executor):
    """
    Обрабатывает все растровые изображения в указанной директории.

    Этот метод проходит по всем файлам в указанной директории, находит все файлы с расширением '.tif' и запускает
    асинхронную обрезку каждого файла.

    Параметры:
    ----------
    input_dir : str
        Путь к директории, содержащей входные файлы.
    output_base_dir : str
        Путь к базовой выходной директории.
    step_multiplier : float
        Множитель для шага обрезки изображения.
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
                tasks.append(crop_image(input_path, output_base_dir, step_multiplier, executor))
                logging.info(f'Started processing {input_path}')  # Логируем начало обработки файла
    await asyncio.gather(*tasks)
    logging.info(f"Processing completed for all files in {input_dir}")  # Логируем завершение обработки директории

if __name__ == "__main__":
    # Запрашиваем путь к корневой директории набора данных
    # print('Enter the path to the root directory for the dataset:')
    # input_path_root_dataset = input().strip()
    INPUT_PATH_ROOT_DATASET = os.getenv("INPUT_PATH_ROOT_DATASET")
    logging.info(f"Path to the root directory for the dataset: {INPUT_PATH_ROOT_DATASET}")

    # Запрашиваем путь к выходной директории
    # print('Enter the path to the output directory:')
    # output_base_dir = input().strip()
    OUTPUT_BASE_DIR = os.getenv("OUTPUT_BASE_DIR")
    logging.info(f"Path to the output directory: {OUTPUT_BASE_DIR}")

    # Запрашиваем множитель для шага обрезки
    # print('Enter the step multiplier (e.g., 0.25 for 25% step):')
    # step_multiplier = float(input().strip())
    STEP_MULTIPLIER = float(os.getenv("STEP_MULTIPLIER"))
    logging.info(f"step multiplier: {STEP_MULTIPLIER}")

    # Создаем экзекутор с количеством рабочих потоков, равным количеству ядер процессора
    executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    # Запускаем асинхронную обработку директории
    asyncio.run(process_directory(INPUT_PATH_ROOT_DATASET, OUTPUT_BASE_DIR, STEP_MULTIPLIER, executor))
