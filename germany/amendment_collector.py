import logging

from common import pdf_parser, text_utils
from common.record import BILL_STATUS_REJECTED, BILL_STATUS_PASSED
from common.utils import bs4_parse
from germany import mongo_initializer, selenium_page_downloader, db_handler
from germany.common_utils import *


def collect_amendment_pages():
    logging.info('Collecting amendment pages for all bills...')

    for record in get_relevant_records():
        logging.info(f'Processing bill {record["record_id"]}')

        for am in record['amendments']:
            if am['amendment_page_link']:
                selenium_page_downloader.download_page(
                    am['amendment_page_link'], mongo_initializer.get_amendment_pages_collection()
                )


def process_amendments(record: dict):
    logging.info(f'Processing bill {record["record_id"]}')

    for existing_amendment in record['amendments']:
        stored_page = mongo_initializer.get_amendment_pages_collection().find_one(
            {'url': (existing_amendment['amendment_page_link'])}
        )

        if stored_page is not None:
            new_variables = process_amendment_page(stored_page)
            existing_amendment.update(new_variables)

            logging.info(f'Processed amendment: {stored_page["url"]}')
        else:
            logging.error(f'Amendment page not stored in DB: {existing_amendment["amendment_page_link"]}')

    mongo_initializer.get_records_collection().update_one(
        {'_id': record['_id']},
        {'$set': {'amendments': record['amendments']}}
    )

    logging.info(f'Updated record: {record["record_id"]}')


def process_amendment_page(stored_page: dict) -> dict:
    parsed_page = bs4_parse(stored_page['source'])

    return {
        'amendment_id': get_label_text(parsed_page, 'ID:'),
        'amendment_outcome': parse_outcome(parsed_page),
        'amendment_text_url': parse_text_link(parsed_page),
        'amendment_originator': parse_originator(parsed_page),
        'amendment_originator_aff': parse_originator_aff(parsed_page)
    }


def parse_outcome(page: BeautifulSoup) -> str:
    status_text = get_label_text(page, 'Beratungsstand:')

    if status_text in ['Verkündet', 'Angenommen']:
        return BILL_STATUS_PASSED
    elif status_text == 'Abgelehnt':
        return BILL_STATUS_REJECTED


def parse_text_link(page: BeautifulSoup) -> str:
    if docs_label := page.find(name='label', text='Wichtige Drucksachen'):
        return docs_label.find_next(name='a').get('href')


def parse_originator(page: BeautifulSoup) -> str:
    if first_stage_header := page.find(name='h3', text=re.compile('Antrag')):
        if orig_list := first_stage_header.find_next(name='ul'):
            names = [
                li.text.replace('Antrag:', '').strip()
                for li
                in orig_list.find_all(name='li')
                if 'und andere' not in li.text
            ]

            return '; '.join(names)


def parse_originator_aff(page: BeautifulSoup) -> str:
    return get_label_text(page, 'Initiative:')


def process_all_amendments():
    for record in get_relevant_records():
        process_amendments(record)


def collect_amendment_texts():
    for record in get_relevant_records():
        updated = False

        for amd in record['amendments']:
            if amd['amendment_text_url'] is not None and amd['amendment_text'] is None:
                full_text = pdf_parser.download_pdf_text(
                    amd['amendment_text_url'], mongo_initializer.get_amendment_text_pdfs_collection()
                )

                text = find_relevant_block(full_text)

                amd['amendment_text'] = text
                amd['amendment_text_size'] = text_utils.get_length_without_whitespace(text)

                updated = True

        if updated:
            mongo_initializer.get_records_collection().update_one(
                {'_id': record['_id']},
                {'$set': {'amendments': record['amendments']}}
            )

            logging.info(f'Updated record: {record["record_id"]}')


def find_relevant_block(pdf_text: str) -> str:
    if pdf_text is not None:
        return pdf_text[pdf_text.find('II.'):]


def get_relevant_records():
    return db_handler.get_records(filter={'amendments': {'$ne': None}})


def fix_amendment_houses():
    for rec in get_relevant_records():
        for am in rec['amendments']:
            if am['amendment_plenary'].lower() == 'bundestag':
                am['amendment_plenary'] = 'LOWER'
            elif am['amendment_plenary'].lower() == 'bundesrat':
                am['amendment_plenary'] = 'UPPER'

        mongo_initializer.get_records_collection().update_one(
            {'_id': rec['_id']},
            {'$set': {'amendments': rec['amendments']}}
        )


def fix_am_orig_aff():
    for rec in get_relevant_records():
        for am in rec['amendments']:
            page = mongo_initializer.get_amendment_pages_collection().find_one({'url': am.get('amendment_page_link')})

            if page:
                parsed = bs4_parse(page.get('source'))
                am['amendment_originator_aff'] = parse_originator_aff(parsed)

        mongo_initializer.get_records_collection().update_one(
            {'_id': rec['_id']},
            {'$set': {'amendments': rec['amendments']}}
        )

        print(f'Updated record: {rec["record_id"]}')
