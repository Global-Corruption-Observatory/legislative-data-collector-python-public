import logging
import re

from selenium import webdriver
from selenium.webdriver.common.by import By

import mongo_initializer

DUPLICATION_CHECK = True
IMPLICIT_WAIT_SECONDS = 10
NUM_ROWS = 250
URL_TEMPLATE = 'https://dip.bundestag.de/erweiterte-suche' \
               '?f.typ=Vorgang' \
               '&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen' \
               '&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung' \
               '&f.drucksachetyp_p=05Gesetze' \
               '&f.drucksachetyp_p=05Gesetze~Gesetzentwurf' \
               '&start={start}' \
               '&rows={rows}' \
               '&sort=basisdatum_ab'

links_collection = mongo_initializer.get_bill_links_collection()


def collect_links():
    current_start = 0
    browser = webdriver.Chrome()
    browser.implicitly_wait(IMPLICIT_WAIT_SECONDS)

    while True:
        logging.info(f'Visiting page starting at: {current_start}')

        page_url = URL_TEMPLATE.format(start=current_start, rows=NUM_ROWS)
        browser.get(page_url)
        link_elements = browser.find_elements(By.CSS_SELECTOR, 'a[title="Einzelansicht öffnen"]')

        if not link_elements:
            break

        links = [remove_search_params(link.get_attribute('href')) for link in link_elements]

        if DUPLICATION_CHECK:
            if existing := list(filter(lambda link: links_collection.count_documents({'bill_link': link}) > 0, links)):
                logging.info(f'Found {len(existing)} existing links')

                for link in existing:
                    links.remove(link)

        if links:
            stored_docs = [{'bill_link': link} for link in links]
            links_collection.insert_many(stored_docs)
            logging.info(f'Stored {len(links)} links')

        current_start += NUM_ROWS

    print('Finished collecting links')


def remove_search_params(orig_url: str) -> str:
    to_remove = '\?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.drucksachetyp_p=05Gesetze&f.drucksachetyp_p=05Gesetze~Gesetzentwurf(&start=\d+)?&rows=250&sort=basisdatum_ab&pos=\d+'

    regex = re.compile(to_remove)

    return regex.sub('', orig_url)

