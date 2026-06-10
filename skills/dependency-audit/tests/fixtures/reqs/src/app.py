import requests
import yaml


def get_data(url):
    return requests.get(url).json()
