# Используем базовый образ Ubuntu
FROM nvidia/cuda:12.3.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Установка временной зоны (например, Europe/London)
RUN ln -sf /usr/share/zoneinfo/Europe/London /etc/localtime

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    wget \
    curl \
    git \
    libopenblas-dev \
    libomp-dev \
    libgfortran5 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Faiss через pip
RUN pip3 install --no-cache-dir faiss-cpu

# Устанавливаем дополнительные библиотеки, если нужно
RUN pip3 install --no-cache-dir numpy scipy
RUN pip3 install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html

ENV PATH="/usr/local/bin:${PATH}"

# Устанавливаем рабочую директорию
WORKDIR /app

COPY faiss_search/ /app/faiss_search

# Копируем текущие файлы в рабочую директорию контейнера
COPY extracting_features_from_layout.py config.py /app
COPY utils/ /app/utils

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

# Указываем команду по умолчанию
CMD ["python3", "extracting_features_from_layout.py"]
