import logging
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http import HTTPStatus
from time import sleep

from bs4 import BeautifulSoup
from bson import InvalidDocument
from pymongo.collection import Collection
from requests import ConnectionError
from urllib3.exceptions import MaxRetryError, ProtocolError, NewConnectionError

import mongo_initializer
from common.date_utils import parse_date_expr
from common.proxy_utils import get_with_proxy
from common.record import Amendment
from common.text_utils import get_length_without_whitespace
from common.utils import bs4_parse, format_date
from common_constants import SITE_HOST

records_collection: Collection = mongo_initializer.get_records_collection()
pages_collection: Collection = mongo_initializer.get_bill_pages_collection()

sys.setrecursionlimit(2500)

def collect_all_amendments():
    filter = {'$and': [{'amendments': {'$eq': None}}, {'amendment_count': {'$gt': 0}}]}

    for record in records_collection.find(filter=filter):
        collect_amendments_for_bill(record)


def collect_amendments_for_bill(record: dict):
    record['amendments'] = []
    logging.info(f"Processing amendments for bill: {record['bill_page_url']}")

    for link in record['amendment_links']:
        try:
            record['amendments'].extend(process_amendments_page(SITE_HOST + link, 1))
        except (ConnectionError, MaxRetryError, NewConnectionError, ProtocolError, ConnectionResetError):
            logging.error(f'Exception when calling URL: {SITE_HOST + link}')
            traceback.print_exc()
            sleep(10)

    try:
        records_collection.update_one({'_id': record['_id']}, {'$set': {'amendments': record['amendments']}})
    except InvalidDocument:
        traceback.print_exc()


def process_amendments_page(page_url: str, current_page: int) -> list:
    results = []

    if (am_page_resp := get_with_proxy(page_url)).status_code == HTTPStatus.OK:
        # todo store in DB
        parsed_am_page = bs4_parse(am_page_resp.text)
        am_table = parsed_am_page.find(name='tbody', id='tbody-amendements-list')

        with ThreadPoolExecutor(max_workers=5) as pool:
            tasks = [pool.submit(parse_amendment, row) for row in am_table.find_all(name='tr')]
            amendments = [task.result() for task in tasks if task.result()]
            results.extend(amendments)

        if pager := parsed_am_page.find(name='div', class_='an-pagination'):
            buttons = pager.find_all(name='div', class_='an-pagination--item')
            max_page: int = int(buttons[-2].text.replace('\n', '').strip())  # get label from second to last button

            logging.info(f'Processed amendments page {current_page}/{max_page}: {page_url}')

            if current_page < max_page:
                next_page = current_page + 1
                next_page_url = page_url.replace(f'&page={current_page}',
                                                 f'&page={next_page}') if current_page > 1 else page_url + '&page=' + str(
                    next_page)
                process_amendments_page(next_page_url, next_page)
    else:
        logging.info(f'Wrong response received ({am_page_resp.status_code}) from URL: {page_url}')

    return results


def parse_amendment(row: BeautifulSoup) -> dict:
    OUTCOME_MAPPING = {
        'Adopté': 'ACCEPTED',
        'Rejeté': 'REJECTED',
        'Non soutenu': 'REJECTED',
        'Tombé': 'REJECTED',
        'Retiré': 'REJECTED',
        'Irrecevable': 'INADMISSIBLE',
        'Non renseigné': None
    }

    cells = row.find_all(name='td')
    num = cells[1].text.strip()
    status = cells[5].text.strip()
    date = cells[7].text.strip()

    # todo set plenary
    result = Amendment()
    result.amendment_id = num
    result.amendment_date = format_date(parse_date_expr(date))

    if status in OUTCOME_MAPPING:
        result.amendment_outcome = OUTCOME_MAPPING.get(status)
    elif status:
        logging.error(f'Unmapped amendment outcome: {status}')

    if details_link := row.get('data-href'):
        result.amendment_text_url = details_link

        try:
            if (details_resp := get_with_proxy(SITE_HOST + details_link)).status_code == HTTPStatus.OK:
                # todo store in DB
                details_page = bs4_parse(details_resp.text)

                if details_div := details_page.find(name='div', class_=''):
                    if stage_label := details_div.find(name='b', text=re.compile('Stade de lecture')):
                        result.amendment_stage_name = stage_label.find_next(name='span').text

                    if committee_label := details_div.find(name='b', text=re.compile('Examiné par')):
                        result.amendment_committee = committee_label.find_next(name='span').text

                if author_list := details_page.find(name='div', class_='acteur-list-embed'):
                    result.amendment_originator = [li.text.strip() for li in author_list.find_all(name='li')]

                if am_text_divs := details_page.find_all(name='div', class_='amendement-section-body'):
                    if len(am_text_divs) > 1:
                        result.amendment_text = am_text_divs[1].parent.text.strip()
                        result.amendment_text_size = get_length_without_whitespace(result.amendment_text)
            else:
                logging.error(f'Wrong response received ({details_resp.status_code}) from URL: {details_link}')
        except (ConnectionError, MaxRetryError):
            logging.error(f'Exception when calling URL: {SITE_HOST + details_link}')
            traceback.print_exc()
            sleep(10)

    return asdict(result)
