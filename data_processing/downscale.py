import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine

def save_raster_with_new_pixel_size_sync(input_path, output_path, new_pixel_size):
    with rasterio.open(input_path) as dataset:
        new_transform = Affine(new_pixel_size[0], 0, dataset.transform.c,
                               0, -new_pixel_size[1], dataset.transform.f)

        new_width = int(dataset.width * (dataset.transform.a / new_pixel_size[0]))
        new_height = int(dataset.height * (-dataset.transform.e / new_pixel_size[1]))

        new_meta = dataset.meta.copy()
        new_meta.update({
            'transform': new_transform,
            'width': new_width,
            'height': new_height,
            'driver': 'GTiff',
            'crs': dataset.crs
        })

        data = dataset.read(
            out_shape=(
                dataset.count,
                new_height,
                new_width
            ),
            resampling=Resampling.bilinear
        )

        with rasterio.open(output_path, 'w', **new_meta) as dest:
            dest.write(data)

async def save_raster_with_new_pixel_size(input_path, output_path, new_pixel_size, executor):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, save_raster_with_new_pixel_size_sync, input_path, output_path, new_pixel_size)

async def downscale(input_dir, executor):
    resolutions = [
        (50, 50), (50, 60), (50, 70), (50, 80),
        (60, 50), (60, 60), (60, 70), (60, 80),
        (70, 50), (70, 60), (70, 70), (70, 80),
        (80, 50), (80, 60), (80, 70), (80, 80)
    ]

    tasks = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.tif'):
                input_path = os.path.join(root, file)
                filename = os.path.basename(input_path)
                base_name = os.path.splitext(filename)[0]
                base_dir = os.path.dirname(input_path)

                original_dir = os.path.join(base_dir, 'original')
                os.makedirs(original_dir, exist_ok=True)

                original_output_path = os.path.join(original_dir, filename)
                with rasterio.open(input_path) as src:
                    with rasterio.open(original_output_path, 'w', **src.meta) as dest:
                        dest.write(src.read())

                for res in resolutions:
                    output_dir = os.path.join(base_dir, 'downscale', f'{base_name}_downscale')
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f'{base_name}_downscale_{res[0]}x{res[1]}.tif')
                    tasks.append(save_raster_with_new_pixel_size(input_path, output_path, res, executor))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    print('Enter the path to the root directory for the dataset:')
    input_path_root_dataset = input().strip()

    executor = ThreadPoolExecutor(max_workers=os.cpu_count())
    asyncio.run(downscale(input_path_root_dataset, executor))