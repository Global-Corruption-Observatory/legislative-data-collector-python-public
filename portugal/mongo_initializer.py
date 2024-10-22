import pymongo
from pymongo.collection import Collection

from common.mongo_initializer import MONGO_URL

MONGO_DATABASE = 'portugal_scraping_recollect'
BILL_PAGES_COLLECTION_NAME = 'bill_pages'
BILL_TEXT_PDFS_COLLECTION_NAME = 'bill_text_pdfs'
RECORDS_COLLECTION_NAME = 'records'
COMMITTEE_PAGES_COLLECTION_NAME = 'committee_pages'
COMMITTEE_REPORT_TEXT_PDFS_COLLECTION_NAME = 'committee_text_pdfs'
LAW_TEXT_PDFS_COLLECTION_NAME = 'law_text_pdfs'
IA_TEXT_PDFS_COLLECTION_NAME = 'ia_text_pdfs'
AMENDMENT_TEXT_PDFS_COLLECTION_NAME = 'amendment_text_pdfs'


def get_collection(name) -> Collection:
    return pymongo.MongoClient(MONGO_URL)[MONGO_DATABASE].get_collection(name)


def get_bill_pages_collection() -> Collection:
    return get_collection(BILL_PAGES_COLLECTION_NAME)


def get_bill_text_pdfs_collection() -> Collection:
    return get_collection(BILL_TEXT_PDFS_COLLECTION_NAME)


def get_records_collection() -> Collection:
    return get_collection(RECORDS_COLLECTION_NAME)


def get_committee_pages_collection() -> Collection:
    return get_collection(COMMITTEE_PAGES_COLLECTION_NAME)


def get_committee_report_text_pdfs_collection() -> Collection:
    return get_collection(COMMITTEE_REPORT_TEXT_PDFS_COLLECTION_NAME)


def get_law_text_pdfs_collection() -> Collection:
    return get_collection(LAW_TEXT_PDFS_COLLECTION_NAME)


def get_ia_text_pdfs_collection() -> Collection:
    return get_collection(IA_TEXT_PDFS_COLLECTION_NAME)


def get_amendment_text_pdfs_collection() -> Collection:
    return get_collection(AMENDMENT_TEXT_PDFS_COLLECTION_NAME)
