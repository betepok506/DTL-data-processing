import os
import asyncio
import aiofiles
import rasterio
from rasterio.windows import Window
from concurrent.futures import ThreadPoolExecutor

def crop_image_sync(input_path_layout, output_base_dir):
    with rasterio.open(input_path_layout) as dataset:
        filename = os.path.basename(input_path_layout)
        base_name = os.path.splitext(filename)[0]
        pixel_size_x, pixel_size_y = dataset.res
        crop_size = 256
        step_size = crop_size // 4
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

async def crop_image(input_path_layout, output_base_dir, executor):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, crop_image_sync, input_path_layout, output_base_dir)

async def process_directory(input_dir, output_base_dir, executor):
    tasks = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.tif'):
                input_path = os.path.join(root, file)
                tasks.append(crop_image(input_path, output_base_dir, executor))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    print('Enter the path to the root directory for the dataset:')
    input_path_root_dataset = input().strip()
    print('Enter the path to the output directory:')
    output_base_dir = input().strip()

    executor = ThreadPoolExecutor(max_workers=os.cpu_count())
    asyncio.run(process_directory(input_path_root_dataset, output_base_dir, executor))
