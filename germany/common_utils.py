import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from pymongo.collection import Collection

DATE_REGEX = '\\d{2}\\.\\d{2}\\.\\d{4}'


def parse_date(text: str):
    date_components = text.split('.')

    return datetime(int(date_components[2]), int(date_components[1]), int(date_components[0])).date()


def rearrange_date(date_text: str) -> str:
    date_components = date_text.split('.')

    return f'{date_components[2]}.{date_components[1]}.{date_components[0]}'


def get_dates_by_label(page: BeautifulSoup, label_text: str) -> list:
    if label := page.find(name='label', text=label_text):
        if date_div := label.find_next(name=re.compile('a|span|div')):
            if date_matches := re.compile(DATE_REGEX).findall(date_div.text):
                return [rearrange_date(date) for date in date_matches]

    return [None]  # avoid error on indexing the returned list


def get_label_text(page: BeautifulSoup, label_name: str) -> str:
    if label := page.find(name='label', text=label_name):
        if next_span := label.find_next(name='span'):
            return next_span.text


def fix_urls(collection: Collection, url_field_name: str):
    # remove transient parts (filtering params) for URLs
    counter = 0

    to_remove1 = '\?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe(&start=\d+)?&rows=250&sort=basisdatum_ab&pos=\d+'

    to_remove2 = '\?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.drucksachetyp_p=05Gesetze&f.drucksachetyp_p=05Gesetze~Gesetzentwurf(&start=\d+)?&rows=250&sort=basisdatum_ab&pos=\d+'

    regex1 = re.compile(to_remove1)
    regex2 = re.compile(to_remove2)

    for link in collection.find():
        counter = counter + 1
        orig_link = link.get(url_field_name)

        if regex1.search(orig_link) or regex2.search(orig_link):
            clean = regex2.sub('', regex1.sub('', orig_link))

            collection.update_one(
                {'_id': link.get('_id')},
                {'$set': {url_field_name: clean}}
            )

            logging.info(f'Updated link {counter}: {orig_link} to: {clean}')
        else:
            logging.info(f'Nothing to update for link: {orig_link}')


def remove_duplicates(collection: Collection, url_field_name: str):
    aggs = [{'$sortByCount': f'${url_field_name}'}]
    duplicates = list(collection.aggregate(aggs))

    for item in duplicates:
        if item.get('count') > 1:
            url = item.get('_id')
            dups = list(collection.find({url_field_name: url}))

            for dup in dups[1:]:
                collection.delete_one({'_id': dup.get('_id')})
                logging.info(f'Deleted: {url}')

