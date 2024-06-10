import requests


def retry_request(max_attempts, time_sleep, initial_delay=1.5, backoff_factor=1.5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            exception = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    print(f"Попытка {attempt + 1} Ошибка:", e)
                    exception = e
                    if attempt < max_attempts - 1:
                        # print(f"Повторная попытка через {delay} секунд...")
                        # time.sleep(time_sleep)
                        delay += backoff_factor

            raise RuntimeError(
                f"Не удалось выполнить функцию {func.__name__} после {max_attempts} попыток. Ошибка: {exception}")

        return wrapper

    return decorator


@retry_request(3, 3)
def send_request(url, method="GET", data=None):
    """
    Отправляет запрос на сервер.

    Аргументы:
    url (str): URL сервера.
    method (str): HTTP метод запроса. По умолчанию "GET".
    data (dict): Данные запроса. По умолчанию None.

    Возвращает:
    response (requests.Response): Ответ сервера.
    """

    if method.upper() == "GET":
        response = requests.get(url)
    elif method.upper() == "POST":
        response = requests.post(url, json=data)
    elif method.upper() == "DELETE":
        response = requests.delete(url)
    else:
        raise ValueError("Неподдерживаемый HTTP метод. Поддерживаются только GET и POST.")

    return response


class ApiClient:
    '''Класс реализует функционал взаимодействия с API сервера'''

    def __init__(self, server_url: str):
        self.server_url = server_url

    def add_layer(self, data):
        '''Фунция для добавления ифнормации о подложке в БД'''
        response = send_request(self.server_url + '/api/v1/layers', 'POST', data)
        return response
