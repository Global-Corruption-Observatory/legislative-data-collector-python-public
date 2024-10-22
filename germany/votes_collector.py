import re
from http import HTTPStatus

import requests

import mongo_initializer
from common import pdf_parser
from common.utils import bs4_parse
from germany import db_handler

vote_pdf_links_collection = mongo_initializer.get_vote_pdf_links_collection()
vote_pdfs_collection = mongo_initializer.get_vote_pdfs_collection()

BASE_URL = 'https://www.bundestag.de'
URL_TEMPLATE = 'https://www.bundestag.de/ajax/filterlist/de/parlament/plenum/abstimmung/liste/462112-462112' \
               '?noFilterSet=true' \
               '&offset={offset}'

def fetch_pdf_links():
    offset = 0
    links_per_page = 30  # don't change this, 30 links will be returned always

    while True:
        url = URL_TEMPLATE.format(offset=offset)
        resp = requests.get(url)

        if resp.status_code == HTTPStatus.OK:
            parsed_page = bs4_parse(resp.text)
            if pdf_links := parsed_page.find_all(name='a', href=re.compile('\.pdf$')):
                links = [BASE_URL + link['href'] for link in pdf_links]
                new = [link for link in links if vote_pdf_links_collection.count_documents({'url': link}) == 0]
                stored = [{'url': link} for link in new]

                if stored:
                    vote_pdf_links_collection.insert_many(stored)

                print(f'Stored {len(stored)} new links with offset {offset}')
            else:
                print(f'Reached end at offset {offset}')
                break
        else:
            print(f'Error response {resp.status_code} received for URL: {url}')

        offset += links_per_page


def download_pdfs():
    for stored_link in db_handler.get_vote_pdf_links():
        url = stored_link['url']

        if vote_pdfs_collection.count_documents({'url': url}) > 0:
            print(f'Skipping existing PDF: {url}')
        else:
            if (resp := requests.get(url)).status_code == HTTPStatus.OK:
                file = {'url': url, 'size': len(resp.content), 'content': resp.content}
                vote_pdfs_collection.insert_one(file)
                print(f'Stored PDF with size: {len(resp.content)}, URL: {url}')
            else:
                print(f'Got error response {resp.status_code} for URL: {url}')


# todo extracted text is not stored
def parse_pdfs():
    in_favor_index = 2
    against_index = 3
    abstention_index = 4

    for stored_pdf in db_handler.get_vote_pdfs():
        text = pdf_parser.extract_with_temp_file(stored_pdf['content'])
        first_page = text[:text.find('Seite:')]

        law_id_matches = re.compile('\d+/\d+').findall(first_page)

        if len(law_id_matches) > 0:
            affected_law_id = law_id_matches[-1]

            if vote_numbers_match := re.compile('(\d+\s+){6}').search(text):
                numbers = list(filter(None, vote_numbers_match.group().splitlines()))
                
                if len((numbers)) == 6:
                    in_favor = int(numbers[in_favor_index])
                    against = int(numbers[against_index])
                    abstention = int(numbers[abstention_index])
    
                    matching_bill = mongo_initializer.get_records_collection().find_one(
                        {'final_version_printed_matter_id': affected_law_id}
                    )

                    if matching_bill:
                        mongo_initializer.get_records_collection().update_one(
                            {'_id': matching_bill['_id']},
                            {'$set':
                                 {
                                     'final_vote_for': in_favor,
                                     'final_vote_against': against,
                                     'final_vote_abst': abstention,
                                     'final_votes_pdf_url': stored_pdf['url']
                                 }
                             }
                        )

                        print(f'Stored votes for bill {matching_bill["record_id"]} ({in_favor}, {against}, {abstention})')

