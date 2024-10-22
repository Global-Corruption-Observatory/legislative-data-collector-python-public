import logging
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date
from functools import reduce
from http import HTTPStatus
from re import RegexFlag, Pattern

from bs4 import Tag, ResultSet
from iteration_utilities import unique_everseen
from pymongo.collection import Collection
from pymongo.errors import DocumentTooLarge, WriteError
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

import mongo_initializer
from common import dynamic_page_downloader, pdf_parser, affecting_laws_calculator
from common.date_utils import parse_date_expr
from common.proxy_utils import get_with_proxy
from common.record import Record, Stage, ORIGIN_TYPE_MP, ORIGIN_TYPE_GOV, \
    BILL_STATUS_PASSED, BILL_STATUS_REJECTED, BILL_STATUS_ONGOING, BILL_STATUS_WITHDRAWN
from common.text_utils import clean_text, get_length_without_whitespace
from common.utils import *
from common_constants import SITE_HOST
from france import amendments_scraper

DATE_EXPR_REGEX: str = '([\\d]{1,2}|1er) [\\wûé]{3,} \\d\\d\\d\\d'
SUBMISSION_DATE_PATTERN: str = f'déposé\\(e\\) le[\\w\\s]* ({DATE_EXPR_REGEX})'
PUBLICATION_DATE_PATTERN: str = f'Publiée au Journal Officiel du {DATE_EXPR_REGEX}'

BILL_ID_REGEX: str = 'n°\\s(\\d+)'
LAW_ID_REGEX: str = 'n° (\\d+-\\d+)'
LAW_ID_PATTERN: Pattern = re.compile(LAW_ID_REGEX)
REFERENCED_LAW_REGEX: str = f'loi {LAW_ID_REGEX}'
MODIFICATION_VERBS: list = ['abrogé', 'completé', 'complété', 'supprimé', 'modifié', 'redigé', 'rédigé', 'inseré',
                            'insérés', 'remplacé']
MODIFIED_LAW_REGEXES: list = [f'{REFERENCED_LAW_REGEX} [\\S\\s]{{0,200}} {verb}' for verb in MODIFICATION_VERBS]
MODIFIED_LAW_PATTERNS: list = [re.compile(p, re.MULTILINE) for p in MODIFIED_LAW_REGEXES]

STAGE_NAME_TRANSLATIONS = {
    '1ère lecture': '1st reading',
    '2ème lecture': '2nd reading'
}

THREADS = 5

logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

records_collection: Collection = mongo_initializer.get_records_collection()
senators_collection: Collection = mongo_initializer.get_senators_collection()
an_members_collection: Collection = mongo_initializer.get_an_members_collection()
pages_collection: Collection = mongo_initializer.get_bill_pages_collection()

unique_id_counter: int = None


def parse_pages():
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        for page in pages_collection.find():
            try:
                if records_collection.count_documents({'bill_page_url': page['url']}) == 0:
                    pool.submit(process_page, page)
                else:
                    logging.info(f'Skipping existing bill: {page["url"]}')
            except Exception as e:
                logging.error(f'Error processing page: {page["url"]} - reason: {e}')
                raise e


def parse_single_bill(url: str):
    if stored_page := pages_collection.find_one({'url': url}):
        process_page(stored_page)


def recollect_and_parse_single_bill(url: str):
    stored_page = {
        '_id': 1,
        'url': url,
    }

    browser = webdriver.Chrome()
    browser.get(url)
    stored_page['html_original'] = browser.page_source

    try:
        browser.find_element_by_link_text('Tout le dossier en une page').click()
        stored_page['html_one_page'] = browser.page_source
    except NoSuchElementException:
        pass

    browser.quit()
    process_page(stored_page)


def is_valid_bill_type(page: BeautifulSoup):
    if bill_type_label := page.find(name='p', class_='deputy-healine-sub-title'):
        bill_type = bill_type_label.text.strip()
        return 'Proposition de loi' == bill_type or 'Projet de loi' == bill_type


def process_page(page: dict):
    parsed_page = bs4_parse(page['html_original'])
    parsed_single_page = bs4_parse(page['html_one_page'])
    promulgation_div = parsed_page.find(name='div', id=re.compile('\\d\\d-PROM'))

    if not is_valid_bill_type(parsed_page):
        logging.info(f'Skipping bill by type: {page["url"]}')
        return

    record = Record(bill_page_url=page['url'])

    def parse_bill_title():
        record.bill_title = parsed_page.h1.text

    def parse_bill_type():
        subtitle = parsed_page.find(name='p', class_='deputy-healine-sub-title')

        if subtitle:
            record.origin_type = map_origin_type(subtitle.text)

    def parse_bill_status():
        if promulgation_div:
            record.bill_status = BILL_STATUS_PASSED
        else:
            rejection_heading = parsed_single_page.find(name='h4', text=re.compile('Texte rejeté'))
            withdrawal_heading = parsed_single_page.find(name='h2', text=re.compile('Retrait'))

            if rejection_heading:
                record.bill_status = BILL_STATUS_REJECTED
            elif withdrawal_heading:
                record.bill_status = BILL_STATUS_WITHDRAWN
            else:
                record.bill_status = BILL_STATUS_ONGOING
                record.bill_id = parse_bill_id()

    def parse_bill_id():
        legislature = re.compile('/dyn/(\\d+)/').search(record.bill_page_url).group(1)

        if depot_divs := parsed_page.find_all(name='div', id=re.compile('DEPOT$')):
            if match := re.compile(BILL_ID_REGEX).search(depot_divs[0].text):
                return legislature + '/' + match.group(1)

    def parse_originators():
        if record.origin_type == ORIGIN_TYPE_MP:
            originator_name_list = []
            authors_block = parsed_page.find(name='div', class_='carrousel-auteurs-rapporteurs')

            if authors_block:
                author_divs = authors_block.find_all(name='p', class_='nom-personne')

                if author_divs:
                    author_names = [clean_name(div.find(name='a').string) for div in author_divs]
                    originator_name_list.extend(author_names)

            cosignataires_block = parsed_page.find(name='div', id='cosignataires-liste')

            if cosignataires_block:
                text = cosignataires_block.getText()

                # remove redundant spaces, tabs, period at end of text
                cosig_name_list = re.sub(
                    pattern='\\s\\s|\\t|\\.$', repl='', string=text, flags=RegexFlag.MULTILINE).split(',')
                originator_name_list.extend([clean_name(name) for name in cosig_name_list])

            if len(originator_name_list) > 0:
                record.originators = [build_originator_obj(name) for name in originator_name_list]

    def parse_stages():
        if stage_headers := parsed_single_page.find_all(name='h3'):
            record.legislative_stages = []

            for header in list(stage_headers):
                stg = Stage()
                parts = [part.strip() for part in header.text.split('\n') if part]
                stg.name = parts[0]

                if len(parts) > 1:
                    house_label = parts[1]
                    stg.house = parse_house(house_label)

                stage_text = header.find_next(name='div').text
                date_expr = re.compile(SUBMISSION_DATE_PATTERN).search(stage_text) \
                            or re.compile(DATE_EXPR_REGEX).search(stage_text)

                if date_expr and (stage_date := parse_date_expr(date_expr.group())):
                    stg.date = format_date(stage_date)

                    if 'Dépôt' in stg.name: record.date_introduction = stg.date
                    if 'Promulgation' in stg.name: record.date_passing = stg.date

                record.legislative_stages.append(stg)

        record.stages_count = len(record.legislative_stages)

    def parse_law_id_and_pub_date():
        if promulgation_div:
            if law_id_match := promulgation_div.find(string=LAW_ID_PATTERN):
                record.law_id = LAW_ID_PATTERN.search(law_id_match).group(1)

            if pub_date_expr := promulgation_div.find(string=re.compile(PUBLICATION_DATE_PATTERN)):
                publication_date = parse_date_expr(
                    re.compile(DATE_EXPR_REGEX).search(pub_date_expr).group()
                )

                # save pub date, will be overwritten later if date entering force is different
                # todo example of different date: http://www.senat.fr/application-des-lois/pjl12-176.html
                # todo text pattern on senate page: Cette loi est d'application directe et ne prévoit pas de mesure réglementaire.
                record.date_entering_into_force = format_date(publication_date)

    def parse_bill_text():
        if submission_div := parsed_page.find(name='div', id=re.compile('DEPOT$')):
            rapporteur_left_divs = submission_div.find_all(name='div', class_='cartouche-rapporteur-left')

            if len(rapporteur_left_divs) == 1:
                first_link = rapporteur_left_divs.pop().find(name='a')

                if first_link:
                    bill_page_url = first_link.get('href')

                    if not (bill_page_url.startswith('http://')
                            or bill_page_url.startswith('https://')
                            or bill_page_url.startswith('www.')):
                        bill_page_url = SITE_HOST + bill_page_url

                    record.bill_text_url = bill_page_url

                    try:
                        bill_page_resp = get_with_proxy(bill_page_url)

                        if bill_page_resp.status_code == HTTPStatus.OK:
                            parsed_bill_page = bs4_parse(bill_page_resp.text)

                            if not parsed_bill_page.find(name='em', text=re.compile('Document non encore publié')):
                                bill_text = get_text_block(parsed_bill_page)

                                if bill_text:
                                    record.bill_text = clean_text(bill_text)
                                    record.bill_size = get_length_without_whitespace(record.bill_text)
                                elif pdf_link := parsed_bill_page.find(name='a', text=re.compile('Version PDF')) \
                                                 or parsed_bill_page.find(name='a', href=re.compile('.pdf')):
                                    pdf_url = SITE_HOST + pdf_link.get('href')
                                    bill_text = pdf_parser.download_pdf_text(pdf_url,
                                                                             mongo_initializer.get_bill_text_pdfs_collection())

                                    if bill_text:
                                        record.bill_text_url = pdf_url
                                        record.bill_text = bill_text
                                        record.bill_size = get_length_without_whitespace(bill_text)
                                    else:
                                        logging.warning(f'Failed to get text from PDF: {pdf_url}')
                                else:
                                    logging.warning(
                                        f'Unexpected page format - can not get bill text: {record.bill_page_url}')
                            else:
                                logging.error(
                                    f'Wrong response received ({bill_page_resp.status_code}) from URL: {bill_page_url}')
                    except Exception:
                        logging.error(f'Failed to process bill page: {bill_page_url}')
                        traceback.print_exc()
            else:
                logging.error(f'Unexpected page format - can not get bill text: {record.bill_page_url}')

    def parse_law_text():
        law_page_url = None

        if promulgation_div:
            law_links = promulgation_div.find_all(name='a')

            if len(law_links) > 0:
                law_page_url = law_links[0].get('href')
                record.law_text_url = law_page_url

        if 'law_page_source' not in page and law_page_url:
            law_page_source = dynamic_page_downloader.get_page_source(law_page_url)
            page['law_page_source'] = law_page_source
            pages_collection.update_one(
                {'_id': page['_id']}, {'$set': {'law_page_source': law_page_source}}
            )

        if 'law_page_source' in page:
            parsed_law_page = bs4_parse(page['law_page_source'])
            article_list = parsed_law_page.find(name='ul', id='liste-sommaire')
            footers = parsed_law_page.find_all(name='div', class_='summary-annexe')

            if article_list:
                record.law_text = article_list.text
                record.law_size = get_length_without_whitespace(record.law_text)
            else:
                logging.error(f'Unexpected page format, can not get law text: {record.bill_page_url}')

            if footers:
                record.law_text_footer = reduce(lambda text1, text2: text1 + text2, [f.text for f in footers])

    def parse_procedure_type():
        accelerated_proc_header = parsed_page.find(
            name='strong', text=re.compile('Le Gouvernement a engagé la procédure accélérée')
        )

        record.procedure_type_standard, record.procedure_type_national = \
            ('EXCEPTIONAL', 'Accelerée') if accelerated_proc_header else ('REGULAR', 'Ordinaire')

        # old code
        # if record.law_text_footer:
        #     record.procedure_type = 'EXCEPTIONAL' if 'procédure accélérée' in record.law_text_footer else 'REGULAR'

    def parse_ia_date(ia_text: str) -> str:
        if date_expr := re.compile(DATE_EXPR_REGEX).search(ia_text[0:300]):
            return format_date(parse_date_expr(date_expr.group().lower()))

    def parse_impact_assessment():
        impact_ass_header = parsed_page.find(name='h4', string=re.compile('Etude d\'impact'))

        if impact_ass_header:
            record.ia_dummy = True
            doc_link = impact_ass_header.parent.find('a')

            if doc_link:
                doc_url: str = doc_link.get('href')
                pdf_url = None

                if doc_url.endswith('.pdf'):
                    pdf_url = doc_url
                elif doc_url.endswith('.html'):
                    guessed_pdf_url = doc_url.replace('.html', '.pdf')

                    if get_with_proxy(guessed_pdf_url).status_code == HTTPStatus.OK:
                        pdf_url = guessed_pdf_url

                if pdf_url:
                    if not pdf_url.startswith('http'):
                        pdf_url = SITE_HOST + pdf_url

                    record.ia_text_url = pdf_url
                    record.ia_text = pdf_parser.download_pdf_text(pdf_url,
                                                                  mongo_initializer.get_ia_text_pdfs_collection())
                    record.ia_size = get_length_without_whitespace(record.ia_text)
                elif doc_url:
                    record.ia_text_url = doc_url

                    ia_page_resp = get_with_proxy(doc_url)
                    resp_content_type = ia_page_resp.headers.get('Content-Type')

                    if ia_page_resp.status_code == HTTPStatus.OK and resp_content_type == 'text/html':
                        parsed_ia_page = bs4_parse(ia_page_resp.text)
                        text_div = parsed_ia_page.find(name='div', id='wysiwyg')

                        if text_div:
                            ia_text = clean_text(text_div.get_text())
                            record.ia_text = ia_text
                            record.ia_size = get_length_without_whitespace(ia_text)
                    else:
                        raise AssertionError(
                            f'Wrong response received ({ia_page_resp.status_code} '
                            f'- {resp_content_type}) from URL: {doc_url}'
                        )

                if record.ia_text:
                    record.ia_date = parse_ia_date(record.ia_text)
        else:
            record.ia_dummy = False

    def parse_committees():
        if committee_spans := parsed_single_page.find_all(name='span', class_='commission'):
            committee_list = [parse_committee(span.text) for span in committee_spans]
            unique_comms = unique_everseen(committee_list, key=lambda comm: comm['committee_name'])

            record.committees = list(unique_comms)
            record.committee_count = len(record.committees)

        hearings_headers = parsed_single_page.find_all(
            name='h6', text=re.compile('Agenda et comptes-rendus des réunions')
        )

        if hearings_headers:
            record.committee_hearing_count = 0

            for head in hearings_headers:
                meetings_div = head.find_next_sibling(name='div')

                if meetings_div:
                    record.committee_hearing_count += len(meetings_div.find_all(name='div', class_='reunion'))

    def parse_modified_laws():
        if record.law_text:
            results = []

            for match_list in [p.findall(record.law_text) for p in MODIFIED_LAW_PATTERNS]:
                results.extend(match_list)

            distinct = set(results)

            if distinct:
                record.original_law = False
                record.modified_laws = list(distinct)
                record.modified_laws_count = len(distinct)
            else:
                record.original_law = True

    def parse_votes():
        if 'votes_page_source' not in page:
            parsed_one_page_law = bs4_parse(page['html_one_page'])
            final_reading_div = parsed_one_page_law.find(name='div', id=re.compile('\\d\\d-ANLDEF'))

            if final_reading_div:
                if votes_page_link := final_reading_div.find(name='a', href=re.compile('scrutins')):
                    if 'assemblee-nationale.fr' in votes_page_link.get('href'):
                        votes_page_src = dynamic_page_downloader.get_page_source(votes_page_link.get('href'))
                    else:
                        votes_page_src = dynamic_page_downloader.get_page_source(
                            SITE_HOST + votes_page_link.get('href'))

                    page['votes_page_source'] = votes_page_src
                    pages_collection.update_one(
                        {'_id': page['_id']}, {'$set': {
                            'votes_page_url': votes_page_link.get('href'), 'votes_page_source': votes_page_src
                        }}
                    )

        if 'votes_page_source' in page:
            if chart := bs4_parse(page['votes_page_source']).text:
                chart_text = chart

                votes_in_favor_match = re.search("Pour l'adoption : ([\\d]+)", chart_text)
                votes_against_match = re.search("Contre : ([\\d]+)", chart_text)
                abstention_match = re.search("Abstention : ([\\d]+)", chart_text)

                if votes_in_favor_match is not None:
                    record.final_vote_for = int(votes_in_favor_match.group(1))

                if votes_against_match is not None:
                    record.final_vote_against = int(votes_against_match.group(1))

                if abstention_match is not None:
                    record.final_vote_abst = int(abstention_match.group(1))
    def parse_debates():
        stored_pages_key = 'debate_pages'

        if stored_pages_key not in page or not page[stored_pages_key]:
            # collect pages
            pages = []
            link_elements = parsed_single_page.find_all(name='a', title='Accéder au compte-rendu')

            for link in link_elements:
                debate_page_url = link.get('href')

                if not debate_page_url.startswith('http'):
                    debate_page_url = SITE_HOST + debate_page_url

                try:
                    page_resp = get_with_proxy(debate_page_url)

                    if page_resp.status_code == HTTPStatus.OK:
                        stored_debate = {'url': debate_page_url, 'source': page_resp.text}

                        # parse legislative stage where the debate occurred
                        if stage_header := link.find_previous(name='h3'):
                            stored_debate['parsed_stage'] = parse_stage_obj(stage_header.text)

                        pages.append(stored_debate)
                except Exception:
                    logging.warning(f'Failed to get debate from URL: {debate_page_url}')
                    traceback.print_exc()

            if len(pages) > 0:
                try:
                    page[stored_pages_key] = pages
                    pages_collection.update_one({'_id': page['_id']}, {'$set': {stored_pages_key: pages}})
                except (DocumentTooLarge, WriteError):
                    traceback.print_exc()

        if stored_pages_key in page and page[stored_pages_key]:
            total_debate_size = 0
            record_stages = record.legislative_stages

            for stored_page in page[stored_pages_key]:
                parsed_debate_page = bs4_parse(stored_page['source'])

                if debate_text := get_text_block(parsed_debate_page):
                    total_debate_size += (deb_len := get_length_without_whitespace(debate_text))

                    if current_debate_stage := stored_page.get('parsed_stage'):
                        matching_stages = filter(
                            lambda stg:
                            stg.name == current_debate_stage.get('name') and stg.house == current_debate_stage.get(
                                'house'),
                            record_stages or []
                        )

                        if matching_stage := next(matching_stages, None):
                            if matching_stage.debate_size is None:
                                matching_stage.debate_size = 0

                            matching_stage.debate_size += deb_len

            record.plenary_size = total_debate_size

    def parse_amendment_count():
        if am_links := find_amendment_links():
            am_cnt_regex = re.compile('\\d+')
            record.amendment_count = sum([int(am_cnt_regex.search(link.text).group()) for link in am_links])
            record.amendment_links = [link.getText('href') for link in am_links]

    def find_amendment_links():
        return parsed_single_page.find_all(name='a', class_='link-examen-amendement')

    parse_bill_title()
    parse_bill_type()
    parse_bill_status()
    parse_originators()
    parse_law_id_and_pub_date()
    parse_stages()
    parse_law_text()
    parse_procedure_type()
    parse_impact_assessment()
    parse_committees()
    parse_modified_laws()
    parse_votes()
    parse_debates()
    parse_amendment_count()
    parse_bill_text()

    record.record_id = get_next_record_id()
    records_collection.insert_one(asdict(record))
    logging.info(f'Parsed page: {page["url"]}')


def get_text_block(parsed_page: BeautifulSoup) -> str:
    text_container = parsed_page.find(name='iframe', id='docOpaqueIFrame') \
                     or parsed_page.find(name='div', class_='SYCERON') \
                     or parsed_page.find(name='div', id='wysiwyg') \
                     or parsed_page.find(name='div', id='englobe')

    if text_container:
        if (not text_container.text) and (iframe_url := text_container.get('src')).endswith('.raw'):
            raw_page_resp = get_with_proxy(SITE_HOST + iframe_url)
            if raw_page_resp.status_code == HTTPStatus.OK:
                return bs4_parse(raw_page_resp.text).text

        return text_container.text


def map_origin_type(bill_type: str) -> str:
    if bill_type.lower().startswith('projet'):
        return ORIGIN_TYPE_GOV
    elif bill_type.lower().startswith('proposition'):
        return ORIGIN_TYPE_MP
    else:
        logging.error(f'Unknown origin type: {bill_type}')


def build_originator_obj(originator_name: str) -> dict:
    result = {'originator_name': originator_name}

    sen = senators_collection.find_one({'parsed_name': originator_name})
    an_member = an_members_collection.find_one({'parsed_name': originator_name})

    if sen and 'parsed_affiliation' in sen:
        result['originator_affiliation'] = sen['parsed_affiliation']
    elif an_member and 'parsed_affiliation' in an_member:
        result['originator_affiliation'] = an_member['parsed_affiliation']

    return result


def parse_committee(orig_string: str) -> dict:
    lead_role_name = 'Commission saisie au fond'
    string_parts = split_by_lines(orig_string)

    if len(string_parts) == 2:
        name = string_parts[0]
        role = 'Lead' if string_parts[1] == lead_role_name else 'Advisory'

        return {'committee_name': name, 'committee_role': role}
    else:
        return {'committee_name': orig_string.strip()}


def parse_date_expression(element: Tag) -> date:
    if sub_date := element.find(string=re.compile(SUBMISSION_DATE_PATTERN)):
        return parse_date_expr(re.compile(DATE_EXPR_REGEX).search(sub_date).group())


def parse_earliest_date_expression(element_list: ResultSet) -> str:
    dates = [dt for dt in [parse_date_expression(element) for element in element_list] if dt is not None]

    if len(dates) > 0:
        if earliest_date := min(dates):
            return format_date(earliest_date)


def split_by_lines(orig_str: str) -> []:
    return list(filter(None, map(lambda s: s.strip(), orig_str.splitlines())))


def parse_stage_obj(stage_header: str) -> dict:
    if header_lines := split_by_lines(stage_header):
        return {'name': parse_stage_name(header_lines[0]), 'house': parse_house(header_lines[1])}


def parse_house(orig_house: str) -> str:
    if 'Assemblée nationale' in orig_house:
        return 'LOWER'
    elif 'Sénat' in orig_house:
        return 'UPPER'


def parse_stage_name(orig_name: str) -> str:
    if orig_name in STAGE_NAME_TRANSLATIONS:
        return STAGE_NAME_TRANSLATIONS[orig_name]

    return orig_name


def get_next_record_id():
    global unique_id_counter

    next_id: int = unique_id_counter + 1 if unique_id_counter else records_collection.count_documents({}) + 1
    unique_id_counter = next_id

    return 'FR' + str(next_id).zfill(5)


def fix_amendment_links():
    for record in records_collection.find(filter={'amendment_count': {'$gt': 0}}):
        page = pages_collection.find_one({'url': record['bill_page_url']})
        parsed = bs4_parse(page['html_one_page'])
        links = [link.get('href') for link in parsed.find_all(name='a', class_='link-examen-amendement')]
        records_collection.update_one({'_id': record['_id']}, {'$set': {'amendment_links': links}})
        logging.info(f'Updated {record["_id"]}')


def run_bill_page_parser():
    parse_pages()
    affecting_laws_calculator.calculate_affecting_laws(records_collection)
    amendments_scraper.collect_all_amendments()
