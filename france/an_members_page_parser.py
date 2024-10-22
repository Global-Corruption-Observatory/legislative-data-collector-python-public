import re

import mongo_initializer
from common import utils


def parse_source():
    pages_collection = mongo_initializer.get_an_member_pages_collection()
    an_members_collection = mongo_initializer.get_an_members_collection()

    for page in pages_collection.find():
        record = {'page_id': page['_id']}

        parsed_page = utils.bs4_parse(page['source'])
        header = parsed_page.find('h1')

        if header:
            record['parsed_name'] = utils.clean_name(header.getText())

        span = parsed_page.find(name='span',
                                string=re.compile('Rattachement au titre du financement de la vie politique'))

        if span:
            affiliation = span.find_next_sibling(name='span')
            record['parsed_affiliation'] = affiliation.get_text().strip()

        print('Saving %s' % record)
        an_members_collection.insert_one(record)
