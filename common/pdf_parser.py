import logging
import threading
import traceback
from http import HTTPStatus
from tempfile import NamedTemporaryFile

import requests
from pdfminer.high_level import extract_text
from pymongo.collection import Collection

from common.text_utils import clean_text
from common.utils import print_error


def download_pdf_text(url: str, db_collection: Collection) -> str:
    # todo label scanned files
    clean = clean_url(url)
    is_stored = db_collection.count_documents({'url': clean}) > 0

    try:
        content = None

        if not is_stored:
            pdf_resp = requests.get(clean)

            if pdf_resp.status_code == HTTPStatus.OK \
                    and pdf_resp.headers.get('Content-Type') == 'application/pdf':
                content = pdf_resp.content

                if len(content) < 16_000_000:
                    db_collection.insert_one({'url': clean, 'size': len(content), 'content': content})
                    logging.info(f'Stored PDF: {clean} with size: {len(content)}')
                else:
                    logging.info(f'Skipping storing PDF over size limit: {clean}')
            else:
                logging.warning(f'Wrong response returned for PDF URL ({pdf_resp.status_code} '
                                f'{pdf_resp.headers.get("Content-Type")}) - {clean}')
        else:
            logging.info(f'Fetching PDF from DB: {clean}')
            stored_obj = db_collection.find_one({'url': clean})

            if 'extracted_text' in stored_obj and stored_obj['extracted_text']:
                logging.debug('Returning stored text from DB')
                return stored_obj['extracted_text']

            content = stored_obj['content']

        if content:
            try:
                text = extract_with_temp_file(content)
                db_collection.update_one({'url': clean}, {'$set': {'extracted_text': text}})

                return text
            except Exception:
                print_error(f'Failed to parse PDF from URL: {clean}')
                traceback.print_exc()
    except Exception:
        print_error(clean)
        traceback.print_exc()


def clean_url(url) -> str:
    if '#' in url:
        return url[:url.index('#')]

    return url


def extract_from_file_and_store(path: str, orig_url: str, db_collection: Collection) -> str:
    # todo url fragments are not filtered, duplicates are stored in db!
    exists = db_collection.count_documents({'url': orig_url}) > 0

    if exists:
        stored = db_collection.find_one({'url': orig_url})

        if 'extracted_text' in stored and stored['extracted_text']:
            return stored['extracted_text']
    else:
        try:
            text = extract_with_lock(path)

            try:
                with open(path, 'rb') as file:
                    content = file.read()

                    db_collection.insert_one({
                        'url': orig_url,
                        'size': len(content),
                        'content': content,
                        'extracted_text': text,
                        'text_size': len(text)
                    })
            except:
                logging.error(f'Failed to store PDF in database from URL: {orig_url}')
                traceback.print_exc()

            return text
        except:
            logging.error("Failed to extract text from PDF")
            traceback.print_exc()


def extract_from_file(path: str) -> str:
    try:
        return extract_with_lock(path)
    except:
        logging.error("Failed to extract text from PDF")
        traceback.print_exc()


def extract_with_temp_file(content: bytes) -> str:
    with NamedTemporaryFile() as pdf_file:
        pdf_file.write(content)
        pdf_file.flush()

        return extract_with_lock(pdf_file.name)


def extract_with_lock(path: str):
    logging.info('Extracting PDF text...')

    with threading.Lock():
        return clean_text(extract_text(path))

