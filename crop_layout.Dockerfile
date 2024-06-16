FROM python:3.9-slim

RUN pip install --no-cache-dir rasterio

# Установка рабочей директории
WORKDIR /app

# Копирование вашего кода в контейнер
COPY data_processing/crop_layout.py /app/crop_layout.py

# Установка зависимостей из requirements.txt, если он существует
# COPY requirements.txt /app/requirements.txt
# RUN pip install --no-cache-dir -r /app/requirements.txt || true

# Указание команды по умолчанию для запуска скрипта
CMD ["python", "crop_layout.py"]