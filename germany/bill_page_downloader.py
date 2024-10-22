from concurrent.futures import ThreadPoolExecutor

import mongo_initializer
import selenium_page_downloader
from germany import db_handler

THREADS = 1
PAGE_TIMEOUT_SECONDS = 1
DUPLICATION_CHECK = True

pages_collection = mongo_initializer.get_bill_pages_collection()


def download_pages():
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for link_obj in db_handler.get_bill_links():
            executor.submit(download_page, link_obj['bill_link'])


def download_page(url: str):
    selenium_page_downloader.download_page(url, pages_collection)

