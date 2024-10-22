import logging
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date, timedelta
from http import HTTPStatus
from re import RegexFlag

import dateparser
import parse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

from common import pdf_parser, text_utils
from common.affecting_laws_calculator import *
from common.record import Record, Originator, ORIGIN_TYPE_MP, ORIGIN_TYPE_GOV, BILL_STATUS_PASSED, \
    BILL_STATUS_REJECTED, BILL_STATUS_ONGOING, Amendment, BILL_STATUS_EXPIRED
from common.text_utils import get_length_without_whitespace
from common.utils import format_date, bs4_parse, print_error
from portugal import mongo_initializer

logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

pages_collection = mongo_initializer.get_bill_pages_collection()
records_collection = mongo_initializer.get_records_collection()
bill_text_pdfs_collection = mongo_initializer.get_bill_text_pdfs_collection()
committee_report_text_pdfs_collection = mongo_initializer.get_committee_report_text_pdfs_collection()
law_text_pdfs_collection = mongo_initializer.get_law_text_pdfs_collection()
ia_text_pdfs_collection = mongo_initializer.get_ia_text_pdfs_collection()
amendment_text_pdfs_collection = mongo_initializer.get_amendment_text_pdfs_collection()

HOST_URL = 'https://www.parlamento.pt'

# format is 70/2020 or 58-A/2020
LAW_ID_REGEX = '\\d{1,3}(-\\w)?/\\d{4}'
LAW_MENTION_REGEX = f'Lei n.º {LAW_ID_REGEX}'
BILL_ID_REGEX = '\\d{1,4}/[IVX]+/\\d'
BILL_ID_PATTERN = re.compile(BILL_ID_REGEX)
DATE_REGEX = '^\\d\\d\\d\\d-\\d\\d-\\d\\d$'
PARTY_NAME_REGEX = '[A-Z]+-?[A-Z]+'
REFERENCED_LAW_PATTERNS = [
    re.compile('alteração à lei n.º (\\d+/\\d+)', re.IGNORECASE),
    re.compile('alteração ao decreto\\s?-\\s?lei n.º (\\d+/\\d+)', re.IGNORECASE),
    re.compile('alteração do decreto\\s?-\\s?lei n.º (\\d+/\\d+)', re.IGNORECASE),
    re.compile('altera o decreto\\s?-\\s?lei n.º (\\d+/\\d+)', re.IGNORECASE)
]

THREADS = 1

unique_id_counter: int = None


def recollect_and_parse_single_bill(url: str):
    br = webdriver.Chrome()
    br.get(url)
    main_div = br.find_element(By.ID, 'contentBox')

    if main_div:
        div_src = main_div.get_attribute('outerHTML')
        process_page({'url': url, 'source': div_src})
    else:
        print_error(f'Error - main div not found on page: {url}')

    br.quit()


def parse_bills():
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        cursor = pages_collection.find().batch_size(10)

        for stored_page in cursor:
            if records_collection.count_documents({'bill_page_url': stored_page['url']}) == 0:
                executor.submit(try_process_page, stored_page)
            else:
                logging.info(f'Skipping stored page: {stored_page["url"]}')


def try_process_page(page):
    try:
        record = process_page(page)
        process_law_variables(record, page)
        records_collection.insert_one(asdict(record))
    except:
        logging.error(f"Failed to process page: {page['url']}")
        traceback.print_exc()


def process_page(stored_page):
    record = Record()
    record.bill_page_url = stored_page['url']
    record.country = 'PORTUGAL'

    logging.info(f'Processing page: {stored_page["url"]}')
    parsed_page = bs4_parse(stored_page['content_box_source'])

    # bill id
    page_title_text = parsed_page.find(name='span', class_='Titulo-Cinzento').text
    record.bill_id = BILL_ID_PATTERN.search(page_title_text).group()

    # origin type
    origin_type = page_title_text.replace(record.bill_id, '').strip()
    record.origin_type = map_origin_type(origin_type)

    # bill title
    # more elements exist with these parameters, the first one is correct
    record.bill_title = parsed_page.find(name='span', title='Detalhe do documento') \
        .parent \
        .text \
        .replace('[formato DOC]', '') \
        .replace('[formato DOCX]', '') \
        .replace('[formato PDF]', '') \
        .strip()

    record.originators = parse_originators(parsed_page)
    record.committees = parse_committees(parsed_page)
    record.committee_count = len(record.committees)
    record.committees_depth = parse_committees_depth(parsed_page)
    record.bill_text_url, record.bill_text, record.bill_size = parse_bill_text(parsed_page)
    record.legislative_stages, record.stages_count = parse_stages(parsed_page)
    parse_date_introduction(record)
    parse_date_committee(record)
    parse_date_passing(record)
    record.committee_hearing_count_external = parse_external_hearings(parsed_page)
    record.plenary_size = parse_debate_sizes(parsed_page)

    record.amendments = parse_amendments(parsed_page)
    if record.amendments:
        record.amendment_count = len(record.amendments)

    votes = parse_votes(parsed_page)

    if votes:
        record.final_vote_for = votes.get('In Favor')
        record.final_vote_against = votes.get('Against')
        record.final_vote_abst = votes.get('Abstention')

    record.ia_dummy, \
        record.ia_text_url, \
        record.ia_title, \
        record.ia_text, \
        record.ia_size = parse_impact_assessment(parsed_page)

    publication_label = parsed_page.find(name='span', text='Lei (Publicação DR)')

    if publication_label:
        record.bill_status = BILL_STATUS_PASSED
    else:
        rejection_labels = parsed_page.find_all(name='b', text='Rejeitado')

        if len(rejection_labels) > 0:
            last_label = rejection_labels[-1]
            page_source_lines = stored_page['content_box_source'].count('\n')
            label_line_number = last_label.sourceline

            # check if the label is at the end of the page - should be in last 35% of lines
            if label_line_number > page_source_lines * 0.65:
                if record.date_passing is None:
                    record.bill_status = BILL_STATUS_REJECTED

                votes_label = last_label.find_next(text=re.compile('(Contra:|A Favor:|Abstenção:|unanimidade)'))

                if votes_label:
                    # parse votes for rejection
                    votes_text = votes_label.parent.text
                    votes = parse_votes_text(votes_text)

                    if votes:
                        record.final_vote_for = votes.get('In Favor')
                        record.final_vote_against = votes.get('Against')
                        record.final_vote_abst = votes.get('Abstention')

    if record.bill_status == BILL_STATUS_ONGOING:
        expiry_labels = parsed_page.find_all(name='span', text='Iniciativa Caducada')

        if expiry_labels:
            record.bill_status = BILL_STATUS_EXPIRED

    record.record_id = get_next_record_id()
    logging.info(f'Processed page: {record.bill_page_url}')
    
    return record


def map_origin_type(origin_type: str) -> str:
    if origin_type == 'Proposta de Lei':
        return ORIGIN_TYPE_GOV
    elif origin_type == 'Projeto de Lei':
        return ORIGIN_TYPE_MP
    else:
        logging.error(f'Unknown origin type: {origin_type}')


def parse_originators(parsed_page: BeautifulSoup) -> list:
    originator_links = parsed_page.find_all(name='a', title='Detalhe do autor')
    return [parse_originator(link.text) for link in originator_links]


def parse_originator(text: str) -> Originator:
    if '(' in text and ')' in text:
        affil_start = text.find('(')

        name = text[0:affil_start - 1]
        affil = text[affil_start + 1:-1]

        return Originator(name, affil)
    else:
        return Originator(name=text)


def parse_committees(parsed_page: BeautifulSoup) -> list:
    committee_spans = \
        parsed_page.find_all(name='span', text=re.compile('^comissão de|^comissao de', RegexFlag.IGNORECASE))

    if committee_spans:
        return [{'committee_name': name} for name in set([span.text for span in committee_spans])]

    return []


def parse_committees_depth(parsed_page: BeautifulSoup) -> int:
    # todo missing: https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=37537
    report_header = parsed_page.find(name='div', text=re.compile('Parecer da Comissão', RegexFlag.IGNORECASE))

    if report_header:
        report_link = report_header.find_next(name='a', href=re.compile('\\.pdf'))

        if report_link:
            text = pdf_parser.download_pdf_text(report_link.get('href'), committee_report_text_pdfs_collection)

            if text:
                return text_utils.get_length_without_whitespace(text)

        report_link = report_header.find_next(name='a', href=re.compile('^https://debates.parlamento.pt/')) # handle html...


def parse_bill_text(parsed_page: BeautifulSoup) -> (str, str, int):
    pdf_link = parsed_page.find(name='a', text='[formato PDF]')

    if pdf_link:
        pdf_url = pdf_link.get('href')
        text = pdf_parser.download_pdf_text(pdf_url, bill_text_pdfs_collection)
        size = text_utils.get_length_without_whitespace(text)

        return pdf_url, text, size

    logging.debug('PDF link not found for bill text')

    return None, None, None


def parse_stages(parsed_page: BeautifulSoup) -> (list, int):
    stage_spans = parsed_page.find_all(name='span', text=re.compile(DATE_REGEX))
    stage_tuples = [(parse_date(span.text), span.find_next(name='span').text) for span in stage_spans]
    stages = [{'date': format_date(t[0]), 'name': t[1]} for t in stage_tuples if t]

    return stages, len(stages)


def parse_date(text: str):
    return datetime.strptime(text, '%Y-%m-%d').date()


def parse_date_introduction(record: Record):
    intro_stage = next(filter(lambda stg: stg['name'] == 'Entrada', record.legislative_stages), None)

    if intro_stage:
        record.date_introduction = intro_stage['date']


def parse_date_committee(record: Record):
    committee_stage = \
        next(filter(lambda stg: 'comissão distribuição' in stg['name'], record.legislative_stages), None) \
        or next(filter(lambda stg: 'comissão' in stg['name'], record.legislative_stages), None)

    if committee_stage:
        record.date_committee = committee_stage['date']


def parse_date_passing(record: Record):
    passing_stage = next(filter(lambda stg: stg['name'] == 'Lei (Publicação DR)', record.legislative_stages), None)

    if passing_stage:
        record.date_passing = passing_stage['date']


def parse_impact_assessment(parsed_page: BeautifulSoup) -> (bool, str, str, str, int):
    ia_label = parsed_page.find(name='span', text=re.compile('A. I. G.|A.I.G.'))

    if ia_label:
        pdf_link = ia_label.find_next_sibling(name='a', text='[formato PDF]')

        if pdf_link:
            url = pdf_link.get('href')
            ia_text = pdf_parser.download_pdf_text(url, ia_text_pdfs_collection)
            size = text_utils.get_length_without_whitespace(ia_text)

            return True, url, 'Avaliação Prévia de Impacto de Género', ia_text, size

    return False, None, None, None, None


def parse_votes(parsed_page: BeautifulSoup) -> dict:
    """
    :rtype: dict with keys: in favor, against, abstention
    """
    final_vote_label = parsed_page.find(name='span', text='Votação final global')

    if final_vote_label:
        if votes_label := final_vote_label.find_next(text=re.compile('(Contra:|A Favor:|Abstenção:|unanimidade)')):
            votes_text = votes_label.parent.parent.parent.text

            return parse_votes_text(votes_text)


def parse_votes_text(votes_text: str):
    result = {'In Favor': None, 'Against': None, 'Abstention': None}

    if votes_text:
        lines = votes_text.replace('Contra', '\nContra') \
            .replace('A Favor', '\nA Favor') \
            .replace('Abstenção', '\nAbstenção') \
            .replace('Ausência', '\nAusência') \
            .splitlines()

        lines = list(filter(
            lambda l: l and l.startswith('A Favor') or l.startswith('Contra') or l.startswith('Abstenção'),
            lines
        ))

        votes = {line.split(':')[0]: line.split(':')[1].strip() for line in lines}

        result['In Favor'] = votes.get('A Favor')
        result['Against'] = votes.get('Contra')
        result['Abstention'] = votes.get('Abstenção')

    return result


def parse_amendments(parsed_page: BeautifulSoup) -> list:
    if amendment_labels := parsed_page.find_all(name='span', text='Admissão Proposta de Alteração'):
        results = []

        for label in amendment_labels:
            amendment = Amendment()

            if originator_line := label.find_next(name='span'):
                if orig_text := originator_line.text:
                    if match := re.compile(PARTY_NAME_REGEX).search(orig_text):
                        amendment.amendment_originator = match.group()

            if text_link := label.find_next(name='a', href=re.compile('\\.pdf')):
                amendment.amendment_text_url = text_link.get('href')

                if text := pdf_parser.download_pdf_text(amendment.amendment_text_url, amendment_text_pdfs_collection):
                    amendment.amendment_text = text
                    amendment.amendment_text_size = text_utils.get_length_without_whitespace(text)

            if special_vote_label := parsed_page.find(name='span', text='Votação na especialidade'):
                if special_vote_label.find_next(name='b', text='Aprovado'):
                    amendment.amendment_outcome = 'APPROVED'

                if vote_text_div := special_vote_label.find_next(name='span', text=re.compile('alteração')):
                    votes_label = vote_text_div.find_next(text=re.compile('Favor'))

                    if votes_label:
                        votes_text = votes_label.parent.text
                        amendment.amendment_vote_for, amendment.amendment_vote_against, amendment.amendment_vote_abst = \
                            parse_votes_text(votes_text).values()

            if amendment:
                results.append(amendment)

        return results


def parse_debate_sizes(parsed_page: BeautifulSoup) -> int:
    if general_debate_label := parsed_page.find(name='span', text='Discussão generalidade'):
        if gen_debate_link := general_debate_label.find_next(name='a'):
            debate_page_url = gen_debate_link.get('href')

            if debate_page_url.startswith('https://debates.parlamento.pt'):
                parse_result = parse.parse(
                    'https://debates.parlamento.pt/catalogo/{periodo}/{publicacao}/{serie}/{legis}'
                    '/{sessao}/{numero}/{data}/{pagina}?pgs={start_pg}-{end_pg}&{trailing}',
                    debate_page_url
                )

                if parse_result:
                    parsed_date = dateparser.parse(parse_result['data'])
                    adjusted_date = parsed_date - timedelta(days=1)

                    download_resp = requests.post('https://debates.parlamento.pt/pagina/export', data={
                        'exportType': 'txt',
                        'exportControl': 'paginas',
                        'paginaInicial': parse_result['start_pg'],
                        'paginaFinal': parse_result['end_pg'],
                        'periodo': parse_result['periodo'],
                        'publicacao': parse_result['publicacao'],
                        'serie': parse_result['serie'],
                        'legis': parse_result['legis'],
                        'sessao': parse_result['sessao'],
                        'numero': parse_result['numero'],
                        'data': adjusted_date.strftime('%Y-%m-%d'),
                        'pagina': parse_result['pagina'],
                        'pgs': parse_result['start_pg'] + '-' + parse_result['end_pg'],
                        'exportar': 'Exportar'
                    })

                    if download_resp.status_code == HTTPStatus.OK:
                        debate_text = download_resp.text

                        if debate_text:
                            return text_utils.get_length_without_whitespace(debate_text)
                else:
                    logging.debug(f'Could not parse parameters from URL: {debate_page_url}')


def parse_external_hearings(parsed_page: BeautifulSoup):
    if hearing_labels := parsed_page.find_all(text=re.compile('Audição|Audiência')):
        results: int = 0

        for label in hearing_labels:
            if parent_heading := label.find_previous(name='div', class_='Titulo-Cinzento'):
                if parent_heading.text.strip() == 'Pedidos parecer a':
                    results += 1

        return results


# todo move to bill_page_downloader?
def set_bill_types():
    type_of_law_pages = {
        'Environment': 'https://www.parlamento.pt/Legislacao/Paginas/Legislacao-area-ambiente.aspx',
        'Communications': 'https://www.parlamento.pt/Legislacao/Paginas/Leis-area_ComunicacaoSocial.aspx',
        'Culture': 'https://www.parlamento.pt/Legislacao/Paginas/LegislacaoareaCulturaJuventudeDesporto.aspx',
        'Defense': 'https://www.parlamento.pt/Legislacao/Paginas/Leis_area_Defesa.aspx',
        'Education, science, youth and sports': 'https://www.parlamento.pt/Legislacao/Paginas/Leis_area_Educacao.aspx',
        'International Affairs, Cooperation and Portuguese Communities':
            'https://www.parlamento.pt/Legislacao/Paginas/Legislacao_area_Negocios_Estrangeiros_CPP.aspx',
        'Health': 'https://www.parlamento.pt/Legislacao/Paginas/Leis_area_saude.aspx',
        'Immigration and Refugees': 'https://www.parlamento.pt/Legislacao/Paginas/Leis_area_Imigracao.aspx',
        'Social Security': 'https://www.parlamento.pt/Legislacao/Paginas/legislacao-area-seguranca-social.aspx',
        'Domestic Violence': 'https://www.parlamento.pt/Legislacao/Paginas/Legislacao_AreaViolenciaDomestica.aspx'
    }

    for topic in type_of_law_pages.keys():
        resp = requests.get(type_of_law_pages[topic])

        if resp.status_code == HTTPStatus.OK:
            parsed_page = bs4_parse(resp.text)
            law_links = parsed_page.find_all(name='a', text=re.compile(LAW_MENTION_REGEX))

            law_id_regex = re.compile(LAW_ID_REGEX)
            law_id_list = [law_id_regex.search(link.text).group() for link in law_links]

            for law_id in law_id_list:
                matching_bill = records_collection.find_one({'law_id': law_id})

                if matching_bill:
                    logging.info(f'Found type of law for bill: {matching_bill["bill_page_url"]}')
                    records_collection.update_one(
                        {'_id': matching_bill['_id']}, {'$set': {'bill_type': topic}}
                    )
                else:
                    logging.info(f'Matching bill not found for law ID: {law_id}')


def fill_amendments():
    logging.info("Collecting amendments...")

    for page in pages_collection.find():
        try:
            record = records_collection.find_one({'bill_page_url': page['url']})

            if record:
                parsed_page = bs4_parse(page['content_box_source'])

                ams = parse_amendments(parsed_page)

                if ams:
                    cnt = len(ams)
                    logging.info(f'Found {cnt} amendments for bill: {record["bill_title"]}')
                    amendment_dicts = [asdict(amendment) for amendment in ams if amendment]
                    records_collection.update_one(
                        {'_id': record['_id']}, {'$set': {'amendments': amendment_dicts, 'amendment_count': cnt}}
                    )
        except:
            traceback.print_exc()


def get_next_record_id():
    global unique_id_counter

    next_id: int = unique_id_counter + 1 if unique_id_counter else records_collection.count_documents({}) + 1
    unique_id_counter = next_id

    return 'PT' + str(next_id).zfill(5)


def process_law_variables(record: Record, stored_page):
    parsed_page = bs4_parse(stored_page['content_box_source'])
    law_page_url, law_page_source = fetch_law_page_if_exists(parsed_page)

    if law_page_source:
        record.bill_status = BILL_STATUS_PASSED

        stored_page['law_page_url'] = law_page_url
        stored_page['law_page_source'] = law_page_source

        pages_collection.update_one(
            {'_id': stored_page['_id']},
            {'$set': {'law_page_url': law_page_url, 'law_page_source': law_page_source}}
        )

        logging.info(f'Stored law page: {law_page_url}')

        parsed_law_page = bs4_parse(law_page_source)

        record.law_id = parse_law_id(parsed_law_page)
        record.law_text_url, record.law_text, record.law_size = parse_law_text(parsed_law_page)
        record.modified_laws, record.modified_laws_count = parse_referenced_laws(record)
        record.original_law = False if record.modified_laws_count else True # truthy value: > 1 modified laws
        record.date_entering_into_force = parse_date_entering_force(record)


def fetch_law_page_if_exists(parsed_page: BeautifulSoup) -> (str, str):
    publication_label = parsed_page.find(name='span', text='Lei (Publicação DR)')

    if publication_label:
        law_page_link = publication_label.find_next(name='a', href=re.compile('DetalheDiplomaAprovado.aspx'))

        if law_page_link:
            law_page_url = HOST_URL + law_page_link.get('href')
            law_page_resp = requests.get(law_page_url)

            if law_page_resp.status_code == HTTPStatus.OK:
                return law_page_url, law_page_resp.text

    return None, None


def parse_law_id(parsed_law_page: BeautifulSoup) -> str:
    title_div = parsed_law_page.find(name='div', class_='Titulo-Cinzento')

    if title_div:
        title_text = title_div.find(name='span').text
        law_id = re.compile(LAW_ID_REGEX).search(title_text)

        if law_id:
            return law_id.group()


def parse_law_text(parsed_law_page: BeautifulSoup) -> (str, str, int):
    law_text_link_span = parsed_law_page.find(name='span', text=re.compile('Ver texto'))

    if law_text_link_span:
        if pdf_link := law_text_link_span.find_next_sibling(name='a', text='[formato PDF]'):
            pdf_url = pdf_link.get('href')
            text = pdf_parser.download_pdf_text(pdf_url, law_text_pdfs_collection)

            return pdf_url, text, get_length_without_whitespace(text)

    logging.debug(f'PDF link not found for law text')
    # todo handle different format
    # parsed_law_page.find(name='div', text=re.compile('Publicação:'))

    return None, None, None


def parse_referenced_laws(record: Record) -> (list, int):
    if record.law_text is not None:
        matches = []

        for pattern in REFERENCED_LAW_PATTERNS:
            matches.extend(pattern.findall(record.law_text))

        if matches:
            distinct = set(matches)
            return list(distinct), len(distinct)

    return None, None


def parse_date_entering_force(record: Record) -> str:
    date_text_regex = '\\d{1,2} de (janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro) de \\d\\d\\d\\d'

    if record.law_text and 'Entrada em vigor' in record.law_text:
        lines = record.law_text.splitlines()

        entering_force_line_num = None

        if 'Entrada em vigor' in lines:
            entering_force_line_num = lines.index('Entrada em vigor')
        elif 'Entrada em vigor e produção de efeitos' in lines:
            entering_force_line_num = lines.index('Entrada em vigor e produção de efeitos')

        if entering_force_line_num:
            # get the next 10 lines after the "date entering force" header
            date_ef_text = (' '.join(lines[entering_force_line_num:entering_force_line_num + 10])
                            .replace('  ', ' ').lower())

            publication_stage = next(
                filter(lambda stg: stg['name'] == 'Lei (Publicação DR)', record.legislative_stages), None)

            if publication_stage:
                pub_date: date = dateparser.parse(publication_stage.get('date'))

            if 'no dia seguinte ao da sua publicação' in date_ef_text or 'no dia seguinte à sua publicação' in date_ef_text:
                # publication +1 day
                return format_date(pub_date + timedelta(days=1))
            elif match := re.compile('entra em vigor (\\d{1,3}) dias após').search(date_ef_text):
                # pub. date + X days
                days = int(match.group(1))
                return format_date(pub_date + timedelta(days=days))
            elif 'no primeiro dia do mês seguinte ao da sua publicação' in date_ef_text:
                # first day of month after pub.
                return format_date(date(pub_date.year, pub_date.month + 1, 1))
            elif match := re.compile(date_text_regex).search(date_ef_text):
                # any date expr
                return format_date(dateparser.parse(match.group()))
            elif 'entra imediatamente em vigor' in date_ef_text and pub_date:
                # immediately
                return format_date(pub_date)
