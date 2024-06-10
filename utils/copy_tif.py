"Копирует все вложенные файлы .tif из указанной папки в одну папку"

import os
import shutil
import aiofiles
import asyncio

async def copy_file(src_file, dst_file, semaphore):
    async with semaphore:
        async with aiofiles.open(src_file, 'rb') as fsrc:
            async with aiofiles.open(dst_file, 'wb') as fdst:
                while True:
                    chunk = await fsrc.read(1024 * 1024)  # Чтение файла по 1MB
                    if not chunk:
                        break
                    await fdst.write(chunk)
        shutil.copystat(src_file, dst_file)  # Копирование метаданных

async def copy_tif_files(src_dir, dst_dir, max_concurrent_copies=10):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    semaphore = asyncio.Semaphore(max_concurrent_copies)
    tasks = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.lower().endswith('.tif'):
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dst_dir, file)
                tasks.append(copy_file(src_file, dst_file, semaphore))
                print(f"File copying started: {src_file} -> {dst_file}")

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Пример использования
    source_directory = r'\data\broken_pixels\crop_70x70'
    destination_directory = r'\dataset_small\broken_pixels'

    # Запуск асинхронной функции
    asyncio.run(copy_tif_files(source_directory, destination_directory))