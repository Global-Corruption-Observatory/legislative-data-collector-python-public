import logging
import traceback
from tempfile import NamedTemporaryFile

import camelot.io as camelot
import requests
from pandas import DataFrame, Series

from germany import mongo_initializer, db_handler

MONGO_SIZE_LIMIT = 16_000_000
modified_law_pdfs_collection = mongo_initializer.get_modified_law_pdfs_collection()


def collect_modified_laws():
    logging.info('Collecting modified laws for all bills...')
    filter = {'$and': [{'modified_laws_pdf_url': {'$ne': None}}, {'modified_laws': None}]}

    for record in db_handler.get_records(filter=filter):
        if 'modified_laws_pdf_url' in record and record['modified_laws_pdf_url'] and record['modified_laws'] is None:
            parse_modified_laws(record)


def parse_modified_laws(record: dict):
    law_ids = parse_from_pdf(record['modified_laws_pdf_url'])

    if any(law_ids):
        mongo_initializer.get_records_collection().update_one(
            {'_id': record['_id']},
            {'$set': {'modified_laws': list(law_ids), 'modified_laws_count': len(law_ids)}}
        )

        logging.info(f'Updated record: {record["record_id"]} with modified law count: {len(law_ids)}')


def parse_from_pdf(pdf_file_url: str) -> set:
    results = set()
    pdf_obj = fetch(pdf_file_url)

    if pdf_obj:
        try:
            with NamedTemporaryFile(suffix='.pdf') as pdf_file:
                pdf_file.write(pdf_obj['content'])
                pdf_file.flush()

                tables = camelot.read_pdf(pdf_file.name, pages='2,3,4')

                for table in tables:
                    frame: DataFrame = table.df

                    if len(frame.keys()) == 4 and 'FNA' == frame.get(3).get(0):
                        # modified law ID column
                        col: Series = frame.get(3)
                        law_ids = [law_id for law_id in col[1:].values if law_id]

                        results.update(set(law_ids))
        except IndexError:
            # normal, PDF is less than 3 pages
            logging.error(f'IndexError for PDF: {pdf_file_url}')
        except:
            logging.error(f'Failed to process PDF: {pdf_file_url}')
            traceback.print_exc()

        if len(results) == 0:
            logging.warning(f'Parsed 0 modified laws from PDF: {pdf_file_url}')

    return results


def fetch(pdf_file_url) -> dict:
    pdf_file_url = pdf_file_url.replace(' ', '')
    stored = modified_law_pdfs_collection.find_one({'url': pdf_file_url})

    if not stored:
        resp = requests.get(pdf_file_url)

        if resp.ok:
            stored = {'url': pdf_file_url, 'content': resp.content}

            if len(resp.content) < MONGO_SIZE_LIMIT:
                modified_law_pdfs_collection.insert_one(stored)
                logging.info(f'Stored PDF file: {pdf_file_url}')
            else:
                logging.info(f'Skipping storing PDF with size: {len(resp.content)}')
        else:
            logging.error(f'Http error {resp.status_code}: {pdf_file_url}')

    return stored

