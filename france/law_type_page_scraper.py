from http import HTTPStatus

import requests

import mongo_initializer
from common import utils

AVAILABLE_LEGISLATURES = [12, 13, 14]
URL_TEMPLATE = 'https://www.assemblee-nationale.fr/{0}/documents/index-dossier.asp'

pages_collection = mongo_initializer.get_law_type_pages_collection()


def collect_pages():
    for leg in AVAILABLE_LEGISLATURES:
        page_resp = requests.get(URL_TEMPLATE.format(leg))

        if page_resp.status_code == HTTPStatus.OK:
            pages_collection.insert_one(
                {'legislature': leg, 'page_source': page_resp.text}
            )

            print(f'Saved page: {page_resp.url}')


def parse_pages():
    for page in pages_collection.find():
        parsed_page = utils.bs4_parse(page['page_source'])
        items = parsed_page.find_all(name='p', align='justify')
        headings = [p.text for p in items]

        for heading in headings:
            if ':' in heading:
                parts = [part.strip() for part in heading.split(':')]
                law_type = parts[0]
                title = parts[1]
                if '(' in title:
                    title = title.split('(')[0].strip()

                parsed_record = {'legislature': page['legislature'], 'law_type': law_type, 'title': title}
                print(parsed_record)


collect_pages()
parse_pages()
