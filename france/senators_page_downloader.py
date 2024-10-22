import requests

import mongo_initializer
from common import static_page_downloader, utils

HOST = 'https://archive.nossenateurs.fr'
SENATORS_PAGE = HOST + '/senateurs'

mongo_collection = mongo_initializer.get_senator_pages_collection()


def get_pages():
    list_page_source = requests.get(SENATORS_PAGE).text
    parsed_page = utils.bs4_parse(list_page_source)
    links = [span.find(name='a').get('href') for span in parsed_page.find_all(name='span', class_='list_nom')]

    absolute_links = [HOST + link for link in links]
    static_page_downloader.store_pages(absolute_links, mongo_collection)
