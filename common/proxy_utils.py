import random

import requests
from requests import Response

PROXIES = [
    "http://185.191.144.186:50100",
    "http://141.11.32.17:50100",
    "http://89.46.99.113:50100",
    "http://45.149.154.57:50100",
    "http://51.83.89.157:50100",
    "http://54.37.57.132:50100",
    "http://145.239.99.122:50100",
    "http://193.70.72.66:50100",
    "http://217.182.45.219:50100",
    "http://188.165.191.233:50100"
]

def get_proxy_config() -> dict:
    random_proxy = PROXIES[random.randint(0, len(PROXIES) - 1)]

    return {
        'http:': random_proxy,
        'https:': random_proxy
    }


def get_with_proxy(url: str) -> Response:
    return requests.get(url, proxies=get_proxy_config())
