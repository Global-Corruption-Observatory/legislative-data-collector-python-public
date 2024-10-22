import os
import pathlib
import traceback
from dataclasses import asdict

import polling2
from polling2 import MaxCallException
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from common import pdf_parser, text_utils
from common.record import Record, Committee, Originator, BILL_STATUS_PASSED, BILL_STATUS_REJECTED, BILL_STATUS_ONGOING, \
    ORIGIN_TYPE_GOV, ORIGIN_TYPE_MP, Stage, Amendment
from common.text_utils import get_length_without_whitespace
from common.utils import bs4_parse
from germany import mongo_initializer, ia_text_parser, db_handler, bill_text_parser
from germany.common_utils import *
import os
import pathlib
import traceback
from dataclasses import asdict

import polling2
from polling2 import MaxCallException
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from common import pdf_parser, text_utils
from common.record import Record, Committee, Originator, BILL_STATUS_PASSED, BILL_STATUS_REJECTED, BILL_STATUS_ONGOING, \
    ORIGIN_TYPE_GOV, ORIGIN_TYPE_MP, Stage, Amendment
from common.text_utils import get_length_without_whitespace
from common.utils import bs4_parse
from germany import mongo_initializer, ia_text_parser, db_handler, bill_text_parser
from germany.common_utils import *

DUPLICATION_CHECK = True
PRINTED_MATTER_ID_REGEX = '\d+/\d+'
MODIFYING_LAW_EXPRESSIONS = [
    'wird wie folgt geändert',
    'wird angefügt',
    'wird wie folgt gefasst',
    'werden die Wörter .{0,200}? ersetzt',
    'wird das Wort .{0,200}? gestrichen',
    'wird folgender Satz angefügt',
    'wird folgender Absatz .{0,200}? angefügt',
    'wird folgender .{0,200}? eingefügt',
    'wird aufgehoben'
]

CHROME_IMPLICIT_WAIT = 3
CHROME_DOWNLOAD_FOLDER = pathlib.Path.home().joinpath('de_pdfs')
CHROME_OPTIONS = webdriver.ChromeOptions()
CHROME_OPTIONS.add_experimental_option("prefs", {
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True,
    "plugins.plugins_disabled": ["Chrome PDF Viewer"],
    "download.default_directory": str(CHROME_DOWNLOAD_FOLDER)
})

PLENARY_HOUSE_TRANSLATIONS = {
    'Bundestag': 'LOWER',
    'BT': 'LOWER',
    'Bundesrat': 'UPPER',
    'BR': 'UPPER'
}

bill_pages_collection = mongo_initializer.get_bill_pages_collection()
records_collection = mongo_initializer.get_records_collection()
bill_text_pdfs_collection = mongo_initializer.get_bill_text_pdfs_collection()

unique_id_counter: int = None


def init_download_dir():
    if not CHROME_DOWNLOAD_FOLDER.exists():
        os.mkdir(CHROME_DOWNLOAD_FOLDER)
    else:
        for existing_file in os.listdir(CHROME_DOWNLOAD_FOLDER):
            os.remove(CHROME_DOWNLOAD_FOLDER.joinpath(existing_file))


def collect_origin_type(page: BeautifulSoup) -> str:
    if orig_label := page.find(name='span', text=re.compile('Urheber:')):
        orig_text = orig_label.parent.text

        if 'Bundesregierung' in orig_text:
            return ORIGIN_TYPE_GOV

        return ORIGIN_TYPE_MP


def collect_originators(page: BeautifulSoup, record: Record) -> list:
    if record.origin_type == ORIGIN_TYPE_MP:
        if orig_label := page.find(name='label', text='Initiative:'):
            if list := orig_label.find_next(name='ul'):
                names = [li.text.strip() for li in list.find_all(name='li')]
                return [Originator(name, name) for name in names]
    else:
        if orig_label := page.find(name='span', text=re.compile('Urheber:')):
            affil = orig_label.parent.text.replace('Urheber: Bundesregierung,', '').strip()

            return [Originator('Bundesregierung', affil)]


def collect_bill_status(page: BeautifulSoup) -> str:
    if tags_label := page.find(name='label', text='Beratungsstand:'):
        status_text = tags_label.find_next(name='span').text.strip()

        no_status_labels = [
            'Erledigt durch Ablauf der Wahlperiode',
            'Nicht abgeschlossen - Einzelheiten siehe Vorgangsablauf',
            'Zurückgezogen',
            'Für erledigt erklärt'
        ]

        if status_text == 'Verkündet':
            return BILL_STATUS_PASSED
        elif status_text == 'Abgelehnt':
            return BILL_STATUS_REJECTED
        elif status_text in no_status_labels:
            return None

    return BILL_STATUS_ONGOING


def collect_bill_type(page: BeautifulSoup) -> str:
    if tags_label := page.find(name='label', text='Sachgebiete:'):
        if tags_div := tags_label.find_next(name='div'):
            return ' - '.join(map(lambda li: li.text.strip(), tags_div.find_all(name='li')))


def collect_committees(page: BeautifulSoup) -> (list, int):
    results = []

    if committee_headers := page.find_all(name='h4', text='Ausschüsse:'):
        for header in committee_headers:
            if comm_list := header.find_next(name='ul'):
                comm_names = [li.text.strip() for li in comm_list.find_all(name='li')]
                new_committees = [Committee(name, 'Lead' if '(federführend)' in name else None) for name in comm_names]

                if current_stage_date := re.compile(DATE_REGEX).search(header.parent.parent.parent.text):
                    for comm in new_committees: comm.committee_date = rearrange_date(current_stage_date.group())

                for comm in new_committees:
                    if comm not in results: results.append(comm)

    unique_count = len(set([comm.committee_name for comm in results]))

    return results, unique_count


def collect_committee_date(page: BeautifulSoup):
    if committee_stage_header := page.find(name='h3', text='Empfehlungen der Ausschüsse'):
        if prev_date := committee_stage_header.find_previous(name='span', text=re.compile(DATE_REGEX)):
            return rearrange_date(prev_date.text)


def collect_committee_hearings(page: BeautifulSoup) -> int:
    return len(page.find_all(name='h4', text='Ausschüsse:'))


def collect_stages(page: BeautifulSoup) -> (list, int):
    if stages_div := page.find(name='div', id='content-vorgangsablauf'):
        filters = ['Geschäftsordnungsantrag', 'Einzelpläne', 'Fortsetzung', 'Nachtrag', '(Gesetzentwurf)']

        headers = [
            h for h 
            in stages_div.find_all(name='h3') 
            if ('Durchgang' in h.text or 'Beratung' in h.text) and not any(f for f in filters if f in h.text)
        ]

        house_dates_names_links = [
            (
                h.find_previous(name='span', text=re.compile('^BT$|^BR$')).text,
                h.find_previous(name='span', text=re.compile(DATE_REGEX)).text,
                h.text.strip(),
                h.find_next(name='a').get('href')
            ) for h in headers
        ]

        # todo filter dupes and only keep the earliest? example - has 25 stages: https://dip.bundestag.de/vorgang/gesetz-%C3%BCber-die-feststellung-des-bundeshaushaltsplans-f%C3%BCr-das-haushaltsjahr-2007/8089?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&start=750&rows=250&sort=basisdatum_ab&pos=872
        stages = [
            Stage(date=rearrange_date(date), name=name, house=PLENARY_HOUSE_TRANSLATIONS.get(house), debate_url=link)
            for (house, date, name, link) in house_dates_names_links
        ]

        for idx, stg in enumerate(stages):
            stg.number = idx + 1

        return stages, len(stages)

    return None, None


def collect_plenary_size(page: BeautifulSoup) -> int:
    if plenum_label := page.find(name='label', text='Plenum'):
        if next_list := plenum_label.find_next(name='ul'):
            pdf_links = [link.get('href') for link in next_list.find_all(name='a')]

            text_lengths = [
                text_utils.get_length_without_whitespace(pdf_parser.download_pdf_text(link, None))
                for link
                in pdf_links
            ]

            return sum(text_lengths)


def collect_bill_text_url(page: BeautifulSoup) -> str:
    if docs_label := page.find(name='label', text='Wichtige Drucksachen'):
        if first_link := docs_label.find_next(name='a'):
            first_doc_link = first_link.get('href')

            if first_doc_link.endswith('.pdf'):
                return first_doc_link
            else:
                logging.warning(f'Invalid link found for bill text - not a PDF: {first_doc_link}')


# todo move to common class for all countries?
def download_bill_texts():
    logging.info('Downloading bill text for all bills...')
    cursor = db_handler.get_records(filter={'bill_text_url': {'$ne': None}, 'bill_text': None})

    for record in cursor:
        pdf_text = pdf_parser.download_pdf_text(record['bill_text_url'], bill_text_pdfs_collection)

        bill_text = bill_text_parser.extract_bill_text(pdf_text)
        bill_size = text_utils.get_length_without_whitespace(bill_text)

        records_collection.update_one(
            {'_id': record['_id']},
            {'$set': {'bill_size': bill_size, 'bill_text': bill_text}}
        )

        logging.info(f'Updated record: {record["record_id"]} with text size: {bill_size}')


def parse_original_law(law_text: str) -> bool:
    if law_text:
        return not any([re.compile(expr).search(law_text) for expr in MODIFYING_LAW_EXPRESSIONS])


# todo unit test for law text collection?
def download_law_texts():
    logging.info('Downloading law text for all bills...')
    init_download_dir()

    chrome = webdriver.Chrome(options=CHROME_OPTIONS)
    chrome.implicitly_wait(CHROME_IMPLICIT_WAIT)

    try:
        for record in db_handler.get_records(filter={'law_text': None}):
            try:
                process_law_text_for_record(chrome, record)
            except:
                logging.error(f'Failed to get law text for bill: {record["bill_page_url"]}')
                traceback.print_exc()
    finally:
        chrome.close()


def process_law_text_for_record(chrome: WebDriver, record: dict):
    if record['law_text'] is None:
        bill_page_url = record['bill_page_url']

        if stored_page := bill_pages_collection.find_one({'url': bill_page_url}):
            parsed_page = bs4_parse(stored_page['source'])
            url, size, text = collect_law_text(parsed_page, chrome)

            if url:
                records_collection.update_one(
                    {'_id': record['_id']},
                    {'$set': {'law_text_url': url, 'law_size': size, 'law_text': text}}
                )

                if orig_law := parse_original_law(text):
                    records_collection.update_one(
                        {'_id': record['_id']}, {'$set': {'original_law': orig_law}}
                    )

                logging.info(f'Set law text for bill: {record["record_id"]}')
        else:
            logging.error(f'Skipping law text download - page not found in DB: {bill_page_url}')
    else:
        logging.info(f'Skipping bill with existing law text: {record["record_id"]}')


# todo: law_text_url can be collected with the basic variables
def collect_law_text(page: BeautifulSoup, chrome: WebDriver) -> (str, int, str):
    if proclamation_label := page.find(name='label', text='Verkündung:'):
        if law_link := proclamation_label.find_next(name='a'):
            law_text_url = law_link.get('href')
            chrome.get(law_text_url)

            try:
                iframe_url = chrome.find_element(By.TAG_NAME, 'iframe').get_attribute('src')

                if stored := mongo_initializer.get_law_text_pdfs_collection().find_one({'url': law_text_url}):
                    logging.info(f'Fetching extracted text from database for PDF: {law_text_url}')
                    law_text = stored['extracted_text']
                else:
                    chrome.get(iframe_url)

                    WebDriverWait(chrome, CHROME_IMPLICIT_WAIT).until(
                        expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, 'button#download')))
                    chrome.find_element(By.CSS_SELECTOR, 'button#download').click()

                    files = polling2.poll(
                        target=lambda: os.listdir(CHROME_DOWNLOAD_FOLDER),
                        check_success=lambda file_list: len(file_list) > 0 and file_list[0].endswith('.pdf'),
                        step=5,
                        max_tries=10
                    )

                    if len(files) == 1:
                        f_name = CHROME_DOWNLOAD_FOLDER.joinpath(files[0])
                        law_text = pdf_parser.extract_from_file_and_store(
                            str(f_name),
                            law_text_url,
                            mongo_initializer.get_law_text_pdfs_collection()
                        )
                    else:
                        raise RuntimeError(f'Invalid number of files in download directory: {len(files)}')

                return law_text_url, text_utils.get_length_without_whitespace(law_text), law_text.strip()
            except (NoSuchElementException, MaxCallException):
                logging.warning(f'Expected element not found on page, failed to collect law text: {law_text_url}')

                law_text = '<ERROR>'
                return law_text_url, len((law_text)), law_text
            finally:
                if files := os.listdir(CHROME_DOWNLOAD_FOLDER):
                    for f in files:
                        os.remove(CHROME_DOWNLOAD_FOLDER.joinpath(f))

    return None, None, None


def collect_policy_area(page: BeautifulSoup) -> str:
    if keywords_label := page.find(name='label', text='Schlagwörter:'):
        if text_div := keywords_label.find_next(name='div'):
            return ' - '.join(map(lambda div: div.text, text_div.find_all(name='div')))


def parse_ia_texts():
    logging.info('Parsing impact assessment texts...')

    for record in db_handler.get_records(filter={'bill_text': {'$ne': None}}):
        parse_ia_text(record)


def parse_ia_text(record: dict):
    if record['bill_text_url']:
        full_text = pdf_parser.download_pdf_text(record['bill_text_url'], bill_text_pdfs_collection)

        text1, text2 = ia_text_parser.parse_from_bill_text(full_text)
        size1, size2 = get_length_without_whitespace(text1), get_length_without_whitespace(text2)

        if text1 or text2:
            records_collection.update_one(
                {'_id': record['_id']},
                {'$set':
                     {
                         'ia_dummy': True,
                         'ia_text_url': record['bill_page_url'],
                         'ia_text1': text1,
                         'ia_size1': size1,
                         'ia_text2': text2,
                         'ia_size2': size2
                     }
                 }
            )

            logging.info(f'Updated record: {record["record_id"]} with total text size: {size1 + size2}')


def parse_stored_pages():
    for page in db_handler.get_bill_pages():
        if DUPLICATION_CHECK and records_collection.count_documents({'bill_page_url': page['url']}) > 0:
            logging.debug(f'Skipping page: {page["url"]}')
        else:
            saved_bill = parse_page(page)
            saved_bill.record_id = get_next_record_id()
            records_collection.insert_one(asdict(saved_bill))

            logging.info(f'Processed bill: {saved_bill.record_id}')


def collect_modified_laws_pdf(page: BeautifulSoup) -> str:
    if label := page.find(name='label', text='Archivsignatur:'):
        if link := label.find_next(name='a'):
            return link.get('href')


def collect_leading_committee(page: BeautifulSoup) -> str:
    if stages_div := page.find(name='div', id='content-vorgangsablauf'):
        if committees_header := stages_div.find(name='h4', text='Ausschüsse:'):
            if comm_list := committees_header.find_next(name='ul'):
                lead_name = [li.text for li in comm_list.find_all(name='li') if '(federführend)' in li.text]
                
                if len(lead_name) == 1:
                    return lead_name[0].replace(' (federführend)', '')


# used to connect the final votes PDF to this bill
def collect_final_version_printed_matter_id(page: BeautifulSoup, record: Record):
    if record.bill_status == BILL_STATUS_PASSED:
        if printed_matter_label := page.find(name='label', text='Wichtige Drucksachen'):
            if ul := printed_matter_label.find_next(name='ul'):
                last = ul.find_all(name='li')[-1]

                if doc_id := re.compile(PRINTED_MATTER_ID_REGEX).search(last.text):
                    record.final_version_printed_matter_id = doc_id.group()


def pre_collect_amendments(page: BeautifulSoup, record: Record) -> (list, int):
    # only collect a subset of the variables from the main bill page
    edge_case_results = process_amendments_edge_case(page)

    if any(edge_case_results):
        return edge_case_results

    return process_amendments(page, record)


def process_amendments_edge_case(page: BeautifulSoup):
    if stages_div := page.find(name='div', id='content-vorgangsablauf'):
        if change_request_label := stages_div.find(name='h3', text=re.compile('Änderungsantrag')):
            result = Amendment()
            result.amendment_stage_number = 1
            result.amendment_stage_name = '1. Beratung'

            if orig_label := change_request_label.find_next(name='span', text=re.compile('Urheber')):
                result.amendment_originator_aff = orig_label.parent.text.replace('Urheber:', '').strip()

            if date_label := change_request_label.find_previous(name='span', text=re.compile(DATE_REGEX)):
                result.amendment_date = rearrange_date(date_label.text)

            if plenary_label := change_request_label.find_previous(name='span', text=re.compile("BT|BR")):
                result.amendment_plenary = PLENARY_HOUSE_TRANSLATIONS.get(plenary_label.text)

            if change_request_block := change_request_label.parent:
                if am_text_link := change_request_block.find(name='a'):
                    result.amendment_text_url = am_text_link.get('href')
                    result.amendment_id = re.compile(PRINTED_MATTER_ID_REGEX).search(am_text_link.text).group()

                if originator_labels := change_request_block.find_all(name='strong', text=re.compile('Änderungsantrag')):
                    orig_names = [
                        l.parent.text.replace('Änderungsantrag:', '').strip() for l in originator_labels]
                    result.amendment_originator = '; '.join(orig_names)

            if second_reading_label := stages_div.find(name='h3', text=re.compile('2. Beratung')):
                second_reading_block = second_reading_label.parent
                if decision_header := second_reading_block.find(name='h4', text='Beschluss:'):
                    if dec_list := decision_header.find_next(name='ul'):
                        if matching := [li.text for li in dec_list.find_all(name='li') if result.amendment_id in li.text]:
                            if len(matching) == 1:
                                if 'Ablehnung' in matching[0]:
                                    result.amendment_outcome = BILL_STATUS_REJECTED
                                elif 'Annahme' in matching[0]:
                                    result.amendment_outcome = BILL_STATUS_PASSED

            return [result], 1

    return None, None


def process_amendments(page: BeautifulSoup, record: Record):
    if stages_div := page.find(name='div', id='content-vorgangsablauf'):
        if am_labels := stages_div.find_all(name='div', text=re.compile('Antrag:')):
            am_links_stages_houses_dates = [
                (
                    label.find_next(name='a').get('href'),
                    label.find_previous(name='h3').text.strip(),
                    label.find_previous(name='div', text=re.compile('^Bundestag$|^Bundesrat$')).text,
                    label.find_previous(name='span', text=re.compile(DATE_REGEX)).text
                )
                for label in am_labels
            ]

            am_list = [
                Amendment(
                    amendment_page_link=link,
                    amendment_stage_name=stage,
                    amendment_plenary=PLENARY_HOUSE_TRANSLATIONS.get(house),
                    amendment_date=rearrange_date(date)
                )
                for (link, stage, house, date) in am_links_stages_houses_dates
            ]

            # set stage number
            for amd in am_list:
                matching_stages = [stg for stg in record.legislative_stages if stg.name == amd.amendment_stage_name]

                if matching_stages:
                    amd.amendment_stage_number = matching_stages[0].number

            return am_list, len(am_list)

    return None, None


def collect_stage_debate_sizes():
    logging.info('Downloading stage debates for all bills...')
    cursor = db_handler.get_records(filter={'legislative_stages': {'$exists': True, '$ne': []}})

    for record in cursor:
        unprocessed_stages = [
            stg
            for stg in record['legislative_stages']
            if stg['debate_url'] and not stg['debate_size']
        ]

        if unprocessed_stages:
            for stg in unprocessed_stages:
                text = pdf_parser.download_pdf_text(
                    stg['debate_url'], mongo_initializer.get_stage_debate_pdfs_collection())

                stg['debate_size'] = text_utils.get_length_without_whitespace(text)

            records_collection.update_one(
                {'_id': record['_id']},
                {'$set': {'legislative_stages': record['legislative_stages']}}
            )

            logging.info(f'Updated record: {record["record_id"]}')
        else:
            logging.info(f'Nothing to process for record {record.get("record_id")}')


# replaced by date introduction
def collect_ia_date(page: BeautifulSoup) -> str:
    if stages_div := page.find(name='div', id='content-vorgangsablauf'):
        if intro_stage := stages_div.find_next(name='h3', text=re.compile('Gesetzentwurf')):
            if date_label := intro_stage.find_previous(name='span', text=re.compile(DATE_REGEX)):
                return rearrange_date(date_label.text)


def parse_page(page_obj):
    saved_bill = Record()
    saved_bill.country = 'GERMANY'
    saved_bill.bill_page_url = page_obj["url"]

    logging.info(f'Processing page: {page_obj["url"]}')

    parsed_page = bs4_parse(page_obj['source'])

    if title := parsed_page.find(name='h1'):
        saved_bill.bill_title = title.text

    if id_label := parsed_page.find(name='label', text='ID:'):
        saved_bill.bill_id = id_label.find_next(name='span').text

    saved_bill.bill_status = collect_bill_status(parsed_page)

    saved_bill.date_introduction = get_dates_by_label(parsed_page, 'Wichtige Drucksachen')[0]
    saved_bill.date_passing = get_dates_by_label(parsed_page, 'Verkündung:')[-1]
    saved_bill.date_entering_into_force = get_dates_by_label(parsed_page, 'Inkrafttreten:')[0]
    saved_bill.bill_type = collect_bill_type(parsed_page)
    saved_bill.origin_type = collect_origin_type(parsed_page)
    saved_bill.originators = collect_originators(parsed_page, saved_bill)
    saved_bill.bill_text_url = collect_bill_text_url(parsed_page)
    saved_bill.committees, saved_bill.committee_count = collect_committees(parsed_page)
    saved_bill.committee_hearing_count = collect_committee_hearings(parsed_page)
    # saved_bill.date_committee = collect_committee_date(parsed_page)
    saved_bill.policy_area = collect_policy_area(parsed_page)
    saved_bill.legislative_stages, saved_bill.stages_count = collect_stages(parsed_page)
    saved_bill.modified_laws_pdf_url = collect_modified_laws_pdf(parsed_page)
    saved_bill.leading_committee_name = collect_leading_committee(parsed_page)
    saved_bill.ia_dummy = True
    saved_bill.ia_date = saved_bill.date_introduction
    saved_bill.amendments, saved_bill.amendment_count = pre_collect_amendments(parsed_page, saved_bill)

    collect_final_version_printed_matter_id(parsed_page, saved_bill)

    return saved_bill


# todo fix duplication - use common method
def get_next_record_id():
    global unique_id_counter

    next_id: int = unique_id_counter + 1 if unique_id_counter else records_collection.count_documents({}) + 1
    unique_id_counter = next_id

    return 'DE' + str(next_id).zfill(5)


def recollect_ia_texts():
    for record in db_handler.get_records(filter={'bill_text_url': {'$ne': None}}):
        bill_text_url = record.get('bill_text_url')
        full_text = pdf_parser.download_pdf_text(bill_text_url, bill_text_pdfs_collection)

        text1, text2 = ia_text_parser.parse_from_bill_text(full_text)

        if text1 or text2:
            records_collection.update_one(
                {'_id': record['_id']},
                {'$set':
                    {
                        'ia_date': record.get('date_introduction'),
                        'ia_text_url': bill_text_url,
                        'ia_text': None,
                        'ia_size': None,
                        'ia_text1': text1,
                        'ia_text2': text2,
                        'ia_size1': get_length_without_whitespace(text1),
                        'ia_size2': get_length_without_whitespace(text2)
                    }
                }
            )

            print(f'Updated record: {record["record_id"]}')


def fix_ia_text_urls():
    filter = {'$and': [{'bill_text_url': {'$ne': None}}, {'ia_text1': {'$ne': None}}, {'ia_text_url': None}]}

    for record in db_handler.get_records(filter=filter):
        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'ia_text_url': record.get('bill_text_url')}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_law_text_urls():
    for record in db_handler.get_records(filter={'law_text_url': {'$regex': 'https://www.bgbl.de/xaver/bgbl'}}):
        page = mongo_initializer.get_bill_pages_collection().find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['source'])

        if proclamation_label := parsed.find(name='label', text='Verkündung:'):
            if law_link := proclamation_label.find_next(name='a'):
                law_text_url = law_link.get('href')

                mongo_initializer.get_records_collection().update_one(
                    {'_id': record['_id']},
                    {'$set': {'law_text_url': law_text_url}}
                )


# single-use methods for recollecting wrong values
def fix_bill_texts():
    for record in db_handler.get_records(filter={'bill_text_url': {'$ne': None}}):
        full_text = pdf_parser.download_pdf_text(record.get('bill_text_url'), bill_text_pdfs_collection)
        new_text = bill_text_parser.extract_bill_text(full_text)

        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'bill_text': new_text, 'bill_size': get_length_without_whitespace(new_text)}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_bill_sizes():
    for record in db_handler.get_records(filter={'bill_text': {'$ne': None}}):
        new_size = get_length_without_whitespace(record['bill_text'])

        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'bill_size': new_size}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_committee_hearings():
    for record in db_handler.get_records(filter={'committee_hearing_count': None}):
        page = mongo_initializer.get_bill_pages_collection().find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['source'])

        cnt = collect_committee_hearings(parsed)

        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'committee_hearing_count': cnt}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_stage_numbers():
    for record in db_handler.get_records(filter={'legislative_stages': {'$ne': None}}):
        stage_list = record['legislative_stages']

        if stage_list:
            for idx, stg in enumerate(stage_list):
                stg['number'] = idx + 1

            mongo_initializer.get_records_collection().update_one(
                {'_id': record['_id']},
                {'$set': {'legislative_stages': stage_list}}
            )

            print(f'Updated record: {record["record_id"]}')


def fix_amendment_stage_nums():
    for record in db_handler.get_records(filter={'amendments': {'$ne': None}}):
        for amd in record.get('amendments'):
            matching_stages = [
                stg for stg in record.get('legislative_stages') if stg.get('name') == amd.get('amendment_stage_name')]

            if matching_stages:
                amd['amendment_stage_number'] = matching_stages[0].get('number')

        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'amendments': record.get('amendments')}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_ia_dates():
    filter = {'$and': [{'$or': [{'ia_text1': {'$ne': None}}, {'ia_text2': {'$ne': None}}]}, {'ia_date': None}]}

    for record in db_handler.get_records(filter):
        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'ia_date': record.get('date_introduction')}}
        )

        print(f'Updated record: {record["record_id"]}')


def fix_bill_status():
    for record in db_handler.get_records(filter={'bill_status': BILL_STATUS_ONGOING}):
        page = mongo_initializer.get_bill_pages_collection().find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['source'])

        status = collect_bill_status(parsed)

        if status != BILL_STATUS_ONGOING:
            mongo_initializer.get_records_collection().update_one(
                {'_id': record['_id']},
                {'$set': {'bill_status': status}}
            )

            print(f'Updated record: {record["record_id"]}')


def fix_stages():
    for record in db_handler.get_records(filter={'stages_count': {'$gt': 10}}):
        page = mongo_initializer.get_bill_pages_collection().find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['source'])

        stages, cnt = collect_stages(parsed)

        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'stages_count': cnt, 'legislative_stages': [asdict(s) for s in stages]}}
        )

        print(f'Updated record: {record["record_id"]}')

        # todo recollect debate size!


def fix_amendments():
    for record in db_handler.get_records(filter={'amendment_count': {'$gt': 1}}):
        page = mongo_initializer.get_bill_pages_collection().find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['source'])

        results, cnt = process_amendments_edge_case(parsed)

        if results:
            mongo_initializer.get_records_collection().update_one(
                {'_id': record['_id']},
                {'$set': {'amendment_count': cnt, 'amendments': [asdict(a) for a in results]}}
            )

            print(f'Updated record: {record["record_id"]}')

        # todo recollect amendment texts!


def fix_stage_debate_pdfs():
    for pdf in mongo_initializer.get_stage_debate_pdfs_collection().find():
        url = pdf['url']

        if '#' in pdf['url']:
            clean = url[:url.index('#')]

            mongo_initializer.get_stage_debate_pdfs_collection().update_one(
                {'_id': pdf['_id']},
                {'$set': {'url': clean}}
            )

            print(f'Fixed URL: {url} to {clean}')


def fix_committee_counts():
    for record in db_handler.get_records(filter={'committee_count': {'$gt': 1}}):
        comm_list = record.get('committees')
        unique_count = len(set([comm.get('committee_name') for comm in comm_list]))

        if unique_count != record.get('committee_count'):
            mongo_initializer.get_records_collection().update_one(
                {'_id': record['_id']},
                {'$set': {'committee_count': unique_count}}
            )

            print(f'Updated record: {record["record_id"]}')


def dedup_stage_debate_pdfs():
    # remove duplicates - 4864 volt
    pdfs_collection = mongo_initializer.get_stage_debate_pdfs_collection()
    agg_results = pdfs_collection.aggregate([{'$sortByCount': '$url'}])

    for item in agg_results:
        if item.get('count') > 1:
            url = item.get('_id')
            dups = list(pdfs_collection.find({'url': url}))

            for dup in dups[1:]:
                pdfs_collection.delete_one({'_id': dup.get('_id')})
                logging.info(f'Deleted: {url}')

