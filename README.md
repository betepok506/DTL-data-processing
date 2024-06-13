# Описание

Данный репозиторий содержит код для работы с данными.

В некоторый скриптах используются docker контейнеры, поэтому перед их использованием необходимо его установить [Ссылка](https://www.docker.com/get-started/)

# Конфигурирование

Конфигурирование проекта осуществляется через файл config.py в котором каждый класс является конфигурационным файлом 

# Установка и запуск

Перед началом необходимо создать сеть Docker:
```commandline
docker network create network-aerial-photography
```

Для сборки контейнера создания датасета используйте команду:
```commandline
docker build -t extracting-features-container -f extracting_features.Dockerfile .
```

Для запуска контейнера извлечения признаков используйте команду
```commandline
docker run --gpus all --network=network-aerial-photography -v  D:\\Hackaton\\DTL-data-processing\\weights:/weights -v D:\\Hackaton\\DTL-data-processing\\data:/data -v D:\\Hackaton\\DTL-data-processing\\data\\data_faiss:/data_faiss  -e PATH_TO_WEIGHT='/weights/checkpoint_efficientnet_b0.pth' -e NAME_MODEL='efficientnet_b0' extracting-features-container
```