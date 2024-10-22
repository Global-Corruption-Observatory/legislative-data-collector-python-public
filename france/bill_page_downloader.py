import logging
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

import mongo_initializer
from common import utils

logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

BASE_URL = 'https://www.assemblee-nationale.fr'
BILL_LIST_PAGE_TEMPLATE = BASE_URL + '/dyn/{leg_number}/dossiers'
AVAILABLE_LEGISLATURES = [10, 11, 12, 13, 14, 15, 16]

pages_collection = mongo_initializer.get_bill_pages_collection()

browser = None


def process_page(link):
    bill_url = BASE_URL + link

    if pages_collection.count_documents({'url': bill_url}) == 0:
        browser.get(bill_url)

        saved_doc = {
            'url': bill_url,
            'html_original': browser.page_source,
        }

        try:
            browser.find_element_by_link_text('Tout le dossier en une page').click()
            saved_doc['html_one_page'] = browser.page_source
        except ElementClickInterceptedException:
            logging.warning(
                'Can\'t save html_one_page for bill: %s' % bill_url)
        except NoSuchElementException:
            logging.warning(
                'Can\'t save html_one_page for bill: %s' % bill_url)

        pages_collection.insert_one(saved_doc)
        print('Saved bill: %s' % bill_url)
    else:
        print('Skipping existing bill: %s' % bill_url)


def iterate_on_bill_list():
    for leg_number in AVAILABLE_LEGISLATURES:
        bill_list_url = BILL_LIST_PAGE_TEMPLATE.format(leg_number=leg_number)
        list_page_resp = requests.get(bill_list_url)

        if list_page_resp.status_code == 200:
            parsed_page = utils.bs4_parse(list_page_resp.text)
            bill_list = parsed_page.find(name='ul', class_='liste-dosleg')
            bill_list_items = bill_list.find_all(name='li', class_='pb-4')

            def is_collected_type(li):
                law_type = li.find_all(name='span')[0].text.strip()
                return 'Proposition de loi' == law_type or 'Projet de loi' == law_type

            bill_links = [li.find(name='a').get('href') for li in bill_list_items if is_collected_type(li)]

            print('Found %s links' % len(bill_links))

            for link in bill_links:
                process_page(link)


def collect_bill_pages():
    browser = webdriver.Chrome()
    iterate_on_bill_list()
    browser.quit()
