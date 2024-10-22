import re
import traceback
from re import RegexFlag
from time import sleep

from selenium.common.exceptions import NoSuchElementException, WebDriverException, ElementNotInteractableException, \
    TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

import mongo_initializer
from common import pdf_parser
from common.utils import print_error

WAIT_TIMEOUT = 45
BILL_LIST_PAGE = 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/IniciativasLegislativas.aspx'
LAW_LIST_PAGE = 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DiplomasAprovados.aspx'
REQUIRED_BILL_TYPES = ['Projeto de Lei', 'Proposta de Lei']

# rerun is faster if some legislatures are skipped if possible
SKIPPED_LEGISLATURES = [
    'Legislatura XVI [2024-03-26 a ]',
    'Legislatura XV [2022-03-29 a 2024-03-25]',
    'Legislatura XIV [2019-10-25 a 2022-03-28]',
    'Legislatura XIII [2015-10-23 a 2019-10-24]',
    'Legislatura XII [2011-06-20 a 2015-10-22]',
    'Legislatura XI [2009-10-15 a 2011-06-19]',
    'Legislatura X [2005-03-10 a 2009-10-14]',
    'Legislatura IX [2002-04-05 a 2005-03-09]',
    'Legislatura VIII [1999-10-25 a 2002-04-04]',
    'Legislatura VII [1995-10-27 a 1999-10-24]',
    'Legislatura VI [1991-11-04 a 1995-10-26]',
    'Legislatura V [1987-08-13 a 1991-11-03]',
    'Legislatura IV [1985-11-04 a 1987-08-12]',
    'Legislatura III [1983-05-31 a 1985-11-03]',
    'Legislatura II [1980-11-13 a 1983-05-30]',
    'Legislatura I [1980-01-03 a 1980-11-12]',
    'Legislatura I [1976-06-03 a 1980-01-02]'
]

BILL_ID_REGEX = '\\d{1,4}/[IVX]+/\\d'

pages_collection = mongo_initializer.get_bill_pages_collection()
records_collection = mongo_initializer.get_records_collection()
committee_pages_collection = mongo_initializer.get_committee_pages_collection()


def download_bills(window1, window2):
    window1.get(BILL_LIST_PAGE)
    accept_cookies(window1)

    legislature_selector = Select(window1.find_element(By.CSS_SELECTOR, 'select[title="Legislaturas"]'))
    legislatures = [opt.text for opt in legislature_selector.options if opt.text not in SKIPPED_LEGISLATURES]

    session_selector = Select(window1.find_element(By.CSS_SELECTOR, 'select[title="Sessões Legislativas"]'))
    session_selector.select_by_index(0)

    for current_legislature in legislatures:
        print(f'Collecting {current_legislature}')

        # find element again to avoid stale element ref
        Select(window1.find_element(By.CSS_SELECTOR, 'select[title="Legislaturas"]')).select_by_visible_text(
            current_legislature)

        for current_bill_type in REQUIRED_BILL_TYPES:
            bill_type_selector = Select(window1.find_element(By.CSS_SELECTOR, 'select[title="Tipos de iniciativa"]'))
            bill_type_selector.select_by_visible_text(current_bill_type)

            window1.find_element(By.CSS_SELECTOR, 'input[value=Pesquisar]').click()
            wait_loader(window1)

            current_page = 1

            while True:
                # iterate on links
                bill_links = window1.find_elements(By.CSS_SELECTOR, 'a[title="Detalhe da iniciativa"]')

                if bill_links:
                    bill_urls = [link.get_attribute('href') for link in bill_links]

                    for url in bill_urls:
                        try:
                            process_bill(url, window2)
                        except WebDriverException:
                            print_error(f'Failed to process page: {url}')
                            traceback.print_exc()

                # go to next page
                pager_divs = window1.find_elements(By.CSS_SELECTOR, 'div.pager')

                if pager_divs:
                    pager_div = pager_divs.pop()

                    if current_page % 10 == 0:
                        try:
                            pager_div.find_element(By.LINK_TEXT, '>').click()
                            wait_loader(window1)
                            current_page += 1
                        except NoSuchElementException:
                            print_error("Couldn't find '>' link, last page reached?")
                            break
                    else:
                        try:
                            next_pg_link = pager_div.find_element(By.LINK_TEXT, str(current_page + 1))

                            next_pg_link.click()
                            wait_loader(window1)
                            current_page += 1
                        except NoSuchElementException:
                            print_error(f"Couldn't find link for page {current_page + 1}, last page reached?")
                            break
                        except ElementClickInterceptedException:
                            traceback.print_exc()


def process_bill(url, window):
    page_not_stored = pages_collection.count_documents({'url': url}) == 0

    if page_not_stored:
        window.get(url)
        main_div = window.find_element(By.ID, 'contentBox')

        if main_div:
            div_src = main_div.get_attribute('outerHTML')
            pages_collection.insert_one({'url': url, 'content_box_source': div_src})
            print(f'Saved page: {url}')
        else:
            print_error(f'Error - main div not found on page: {url}')
    else:
        print(f'Skipping stored page: {url}')


def download_committee_pages(window1, window2):
    results = {}

    starting_page = 'https://www.parlamento.pt/sites/COM/Paginas/default.aspx'
    window1.get(starting_page)
    accept_cookies(window1)

    legislature_selector = Select(window1.find_element(By.CSS_SELECTOR, 'select[title="Legislatura"]'))
    legislature_selector.select_by_visible_text('-- Todas as Legislaturas --')
    window1.find_element(By.CSS_SELECTOR, 'input[value=Pesquisar]').click()
    wait_loader(window1)

    committee_links = window1.find_elements(By.CSS_SELECTOR, 'a[title="Detalhe do orgão"]')
    print(f'Found {len(committee_links)} committee links')

    for link in committee_links:
        committee_page = link.get_attribute('href')
        print(f'Parsing committee: {committee_page}')
        window2.get(committee_page)
        accept_cookies(window2)

        meetings_page = window2.find_element(By.CSS_SELECTOR, 'a[title="Reuniões"]')
        meetings_link = meetings_page.get_attribute('href')

        if meetings_link:
            window2.get(meetings_link)

            try:
                current_page = 1

                while True:
                    try:
                        items_div = window2.find_element(By.CSS_SELECTOR, 'div[id$="pnlResults"]')
                        hearing_links = items_div.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf"]')

                        for pdf_link in hearing_links:
                            pdf_link_url = pdf_link.get_attribute('href')
                            comm_meeting_info_in_url = committee_pdf_url_substring(pdf_link_url, 'Fich=')
                            try:
                                comm_document = committee_pages_collection.find_one(
                                    {'url': {'$regex': '.*' + comm_meeting_info_in_url}})
                                text = comm_document['extracted text']
                            except:
                                text = pdf_parser.download_pdf_text(pdf_link_url, committee_pages_collection)

                            if text:
                                # clean text
                                text = text.replace(' | ', '|') \
                                    .replace(' / ', '/') \
                                    .replace('|', '/') \
                                    .replace('n.º ', '') \
                                    .replace(' - ', ' ')

                                bill_id_patterns = [
                                    re.compile(f'Proposta de Lei ({BILL_ID_REGEX})',
                                               flags=RegexFlag.MULTILINE | RegexFlag.IGNORECASE),
                                    re.compile(f'Projeto de Lei ({BILL_ID_REGEX})',
                                               flags=RegexFlag.MULTILINE | RegexFlag.IGNORECASE)
                                ]

                                matches = []
                                for p in bill_id_patterns:
                                    matches.extend(p.findall(text))

                                for bill in matches:
                                    if bill in results:
                                        results[bill] += 1
                                    else:
                                        results[bill] = 1
                    except NoSuchElementException:
                        print_error(
                            f'There are no Meetings matching your search criteria (on page: {window2.current_url}).')
                    try:
                        pager = window2.find_element(By.CSS_SELECTOR, 'div.pager')
                        pager.find_element(By.LINK_TEXT, str(current_page + 1)).click()
                        wait_loader(window2)
                        current_page += 1
                    except NoSuchElementException:
                        print_error(f'Next page link not found on {window2.current_url}')
                        break
            except NoSuchElementException:
                print_error(f'Expected element not found on page: {window2.current_url}')
                traceback.print_exc()

    print('Storing hearing numbers...')

    for bill_id in results.keys():
        # matching_bill = records_collection.find_one({'bill_id': bill_id})
        records_collection.update_one({'bill_id': bill_id}, {'$set': {'committees_hearings': results[bill_id]}})


def wait_loader(window):
    try:
        loader = window.find_element(By.CSS_SELECTOR, 'span.Loading')
        WebDriverWait(window, WAIT_TIMEOUT * 4).until(expected_conditions.visibility_of(loader))
        WebDriverWait(window, WAIT_TIMEOUT * 4).until_not(expected_conditions.visibility_of(loader))
    except TimeoutException:
        traceback.print_exc()


def accept_cookies(window):
    sleep(3)  # wait for consent bar

    try:
        window.find_element(By.CSS_SELECTOR, 'button.consent-give').click()
    except ElementNotInteractableException:
        pass  # was already accepted


def committee_pdf_url_substring(url, delimiter) -> str:
    return url.partition(delimiter)[2]
