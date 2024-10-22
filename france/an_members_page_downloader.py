import requests

import mongo_initializer
from common import static_page_downloader, utils

HOST = 'https://www2.assemblee-nationale.fr'
MEMBERS_PAGE = HOST + '/deputes/liste/alphabetique'

mongo_collection = mongo_initializer.get_an_member_pages_collection()


def get_pages():
    list_page_source = requests.get(MEMBERS_PAGE).text
    parsed_page = utils.bs4_parse(list_page_source)

    member_links = [
        link.get('href') for link
        in parsed_page.find(name='div', id='deputes-list').find_all(name='a')
        if link.get('href') is not None
    ]

    absolute_links = [HOST + link for link in member_links]
    static_page_downloader.store_pages(absolute_links, mongo_collection)