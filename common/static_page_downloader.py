import logging
from http import HTTPStatus

import requests


def store_pages(link_list, mongo_collection):
    for link in link_list:
        if mongo_collection.count_documents({'url': link}) == 0:
            if (resp := requests.get(link)).status_code == HTTPStatus.OK:
                stored_record = {
                    'url': link,
                    'source': (resp.text)
                }

                print('Saved %s' % link)
                mongo_collection.insert_one(stored_record)
            else:
                logging.error(f'Got error response: {resp.status_code} for URL: {link}')
        else:
            print('Skipping existing page: %s' % link)
