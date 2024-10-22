import pymongo
from pymongo.collection import Collection

from common.mongo_initializer import MONGO_URL

MONGO_DATABASE = 'germany_2023_08_22'
BILL_LINKS_COLLECTION_NAME = 'bill_links'
BILL_PAGES_COLLECTION_NAME = 'bill_pages'
BILL_TEXT_PDFS_COLLECTION_NAME = 'bill_text_pdfs'
LAW_TEXT_PDFS_COLLECTION_NAME = 'law_text_pdfs'
STAGE_DEBATE_PDFS_COLLECTION_NAME = 'stage_debate_pdfs'
AMENDMENT_PAGES_COLLECTION_NAME = 'amendment_pages'
VOTE_PDF_LINKS_COLLECTION_NAME = 'vote_pdf_links'
VOTE_PDFS_COLLECTION_NAME = 'vote_pdfs'
MODIFIED_LAWS_PDFS_COLLECTION_NAME = 'modified_laws_pdfs'
AMENDMENT_TEXT_PDFS_COLLECTION_NAME = 'amendment_text_pdfs'
LEG_RECORDS_COLLECTION_NAME = 'records'


def get_collection(name) -> Collection:
    return pymongo.MongoClient(MONGO_URL)[MONGO_DATABASE].get_collection(name)


def get_bill_pages_collection() -> Collection:
    return get_collection(BILL_PAGES_COLLECTION_NAME)


def get_bill_text_pdfs_collection() -> Collection:
    return get_collection(BILL_TEXT_PDFS_COLLECTION_NAME)


def get_law_text_pdfs_collection() -> Collection:
    return get_collection(LAW_TEXT_PDFS_COLLECTION_NAME)


def get_stage_debate_pdfs_collection() -> Collection:
    return get_collection(STAGE_DEBATE_PDFS_COLLECTION_NAME)


def get_amendment_pages_collection() -> Collection:
    return get_collection(AMENDMENT_PAGES_COLLECTION_NAME)


def get_vote_pdf_links_collection() -> Collection:
    return get_collection(VOTE_PDF_LINKS_COLLECTION_NAME)


def get_vote_pdfs_collection() -> Collection:
    return get_collection(VOTE_PDFS_COLLECTION_NAME)


def get_modified_law_pdfs_collection() -> Collection:
    return get_collection(MODIFIED_LAWS_PDFS_COLLECTION_NAME)


def get_amendment_text_pdfs_collection() -> Collection:
    return get_collection(AMENDMENT_TEXT_PDFS_COLLECTION_NAME)


def get_bill_links_collection() -> Collection:
    return get_collection(BILL_LINKS_COLLECTION_NAME)


def get_records_collection() -> Collection:
    return get_collection(LEG_RECORDS_COLLECTION_NAME)

