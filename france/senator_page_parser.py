import re

import mongo_initializer
from common import utils


def parse_source():
    pages_collection = mongo_initializer.get_senator_pages_collection()
    senators_collection = mongo_initializer.get_senators_collection()

    for page in pages_collection.find():
        record = {'page_id': page['_id']}

        parsed_page = utils.bs4_parse(page['source'])
        header = parsed_page.find('h1')

        if header:
            record['parsed_name'] = header.getText()

        informations_header = parsed_page.find(name='h2', string=re.compile('Informations'))

        if informations_header:
            informations_text = informations_header.find_next_sibling(name='ul').get_text()
            match = re.compile('Parti politique \\(rattachement financier\\) : (.+)').search(informations_text)

            if match:
                record['parsed_affiliation'] = match.group(1)

        print('Saving %s' % record)
        senators_collection.insert_one(record)
