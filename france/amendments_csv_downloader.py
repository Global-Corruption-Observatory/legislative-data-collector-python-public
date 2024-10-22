import logging
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from csv import DictReader
from string import Template

import requests
from pymongo.errors import DocumentTooLarge

from common import utils, pdf_parser, text_utils
from common.utils import bs4_parse
from france import mongo_initializer

HOST = 'https://data.assemblee-nationale.fr/'
STARTING_PAGE = HOST + 'dossierLeg/liste-amendements'
BILL_PAGE = Template(STARTING_PAGE + '?idDossier=$id')
OUTCOME_MAPPING = {
    'Adopté': 'ACCEPTED',
    'Rejeté': 'REJECTED',
    'Non soutenu': 'REJECTED',
    'Tombé': 'REJECTED',
    'Retiré': 'REJECTED',
    'Non renseigné': None
}

logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

amendments_collection = mongo_initializer.get_amendments_collection()
an_members_collection = mongo_initializer.get_an_members_collection()
records_collection = mongo_initializer.get_records_collection()


def download_csvs():
    requests_resp = requests.get(STARTING_PAGE)
    parsed_page = utils.bs4_parse(requests_resp.text)
    select = parsed_page.find('select')
    amendment_file_ids = [opt.get('value') for opt in select.find_all('option') if opt.get('value')]
    logging.info(f'Found {len(amendment_file_ids)} bills')

    # skip already downloaded files
    filtered = [id for id in amendment_file_ids
                if amendments_collection.count_documents({'amendment_file_id': amendment_file_ids}) == 0]

    for amendment_file_id in filtered:
        bill_url = BILL_PAGE.substitute(id=amendment_file_id)
        bill_resp = requests.get(bill_url)

        if bill_resp.status_code == 200:
            parsed_bill_page = utils.bs4_parse(bill_resp.text)
            bill_title = parsed_bill_page.find_all('h2')[-1].text.strip()
            csv_link = parsed_bill_page.find(name='a', href=re.compile('excel.csv$'))

            if csv_link:
                logging.info(f'Downloading file for bill: {amendment_file_id} - {bill_title}')

                csv_url = csv_link.get('href')
                csv_resp = requests.get(HOST + csv_url)

                if csv_resp.status_code == 200:
                    csv_content = csv_resp.text
                    csv_dict = DictReader(csv_content.splitlines(), delimiter=';')

                    for row in csv_dict:
                        stored_doc = {
                            'amendment_file_id': amendment_file_id,
                            'amendment_file_url': csv_url,
                            'bill_title': bill_title,
                            **row
                        }

                        amendments_collection.insert_one(stored_doc)


def process_amendments():
    logging.info('Processing downloaded amendments...')

    cursor = records_collection.find(no_cursor_timeout=True)

    with ThreadPoolExecutor(max_workers=15) as executor:
        for bill in cursor:
            executor.submit(process_bill, bill)

    cursor.close()


def process_bill(bill):
    if not bill['amendments']:
        matching_amendments = [*amendments_collection.find({'bill_title': bill['bill_title']})]

        if matching_amendments:
            result_list = []

            num = len(matching_amendments)
            logging.info(f'Found {num} amendments for bill: {bill["bill_title"]}')
            records_collection.update_one({'_id': bill['_id']}, {'$set': {'amendments_count': num}})

            for am in matching_amendments:
                stored_amendment = {
                    'amendment_id': am["Numéro de l'amendement"],
                    'amendment_stage_name': am['Etape du texte']
                }

                if bill_id_match := re.compile('n° (\\d+)$').search(am['Titre complet']):
                    stored_amendment['bill_id'] = bill_id_match.group(1)

                originators = [am['Auteur']]
                originators = [' '.join(o.split(' ')[::-1]) for o in originators]
                originators.extend([name.strip() for name in am['Cosignataire(s)'].split(', ') if name.strip()])
                stored_amendment['originator'] = originators

                if stored_member := an_members_collection.find_one({'parsed_name': originators[0]}):
                    stored_amendment['originator_affiliation'] = stored_member.get('parsed_affiliation')

                outcome_french = am["Sort de l'amendement"]
                stored_amendment['amendment_outcome'] = OUTCOME_MAPPING.get(outcome_french, outcome_french)

                try:
                    am_page_resp = requests.get(am['URL Amendement'])

                    if am_page_resp.status_code == 200:
                        parsed_am_page = bs4_parse(am_page_resp.text)

                        committee_link = parsed_am_page.find(name='b', text=re.compile('Examiné par')).find_next('a')
                        stored_amendment['amendment_committee_name'] = committee_link.text.strip()

                        pdf_link = parsed_am_page.find(name='span', text='Version PDF').parent
                        pdf_url = 'https://www.assemblee-nationale.fr' + pdf_link.get('href')
                        am_text = pdf_parser.download_pdf_text(pdf_url,
                                                               mongo_initializer.get_amendment_text_pdfs_collection())

                        stored_amendment['amendment_text'] = am_text
                        stored_amendment['amendment_text_url'] = pdf_url
                        stored_amendment['amendment_text_size'] = text_utils.get_length_without_whitespace(am_text)

                        if am_text:
                            first_lines = am_text.split('\n', 5)[0:5]

                            if 'ASSEMBLÉE NATIONALE' in first_lines:
                                stored_amendment['amendment_plenary'] = 'LOWER'
                            else:
                                logging.warning(f'Can not determine house from amendment text: {pdf_url}')

                    result_list.append(stored_amendment)
                except Exception:
                    logging.error(f'Failed to get URL: {am["URL Amendement"]}')
                    traceback.print_exc()

            try:
                records_collection.update_one(
                    {'_id': bill['_id']}, {'$set': {'amendments': result_list, 'amendment_count': len(result_list)}}
                )
                logging.info(f'Processed bill: {bill["bill_title"]}')
            except DocumentTooLarge:
                for am in result_list:
                    am['amendment_text'] = '<truncated>'

                try:
                    records_collection.update_one(
                        {'_id': bill['_id']}, {'$set': {'amendments': result_list, 'amendment_count': len(result_list)}}
                    )

                    logging.info(f'Saved amendments with truncated text for bill: {bill["bill_page_url"]}')
                except Exception:
                    logging.error(f'Error saving amendments with truncated text for bill: {bill["bill_title"]}')
                    traceback.print_exc()
            except Exception:
                logging.error(f'Failed to save amendments for bill: {bill["bill_title"]}')
                traceback.print_exc()
    else:
        logging.info(f'Skipping bill with existing amendments: {bill["bill_page_url"]}')


def run_amendments_csv_downloader():
    download_csvs()
    process_amendments()
