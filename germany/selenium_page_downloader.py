import logging
import traceback

from object_pool import ObjectPool
from pymongo.collection import Collection
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

THREADS = 1
PAGE_TIMEOUT_SECONDS = 1
DUPLICATION_CHECK = True

browser_pool: ObjectPool = None


def init_browser_pool():
    global browser_pool
    browser_pool = ObjectPool(webdriver.Chrome, min_init=THREADS, max_capacity=THREADS, max_reusable=0)


def download_page(url: str, db_collection: Collection):
    if DUPLICATION_CHECK:
        if db_collection.count_documents({'url': url}) > 0:
            logging.info(f'Skipping page: {url}')
            return

    if '.pdf' in url:
        logging.error(f'Invalid URL passed to page downloader, skipping: {url}')
        return

    if browser_pool is None:
        init_browser_pool()

    try:
        with browser_pool.get() as (window, _):
            window.implicitly_wait(PAGE_TIMEOUT_SECONDS)

            window.get(url)
            WebDriverWait(window, PAGE_TIMEOUT_SECONDS).until(
                expected_conditions.presence_of_element_located((By.TAG_NAME, 'h1')))

            # check error page
            try:
                if window.find_element(By.XPATH, '//*[contains(text(), "Das sollte eigentlich nicht passieren.")]'):
                    logging.error('Received error page, stopping...')
                    return
            except:
                pass  # element not found is normal

            try:
                if open_all_btn := window.find_element(By.CSS_SELECTOR, 'button[title="Alle Informationen aufklappen"]'):
                    open_all_btn.click()
            except:
                pass  # normal

            saved_doc = {'url': url, 'size': len(window.page_source), 'source': window.page_source}
            db_collection.insert_one(saved_doc)
            logging.info(f'Saved page: {url}')
    except:
        logging.error(f'Error downloading page: {url}')
        traceback.print_exc()
