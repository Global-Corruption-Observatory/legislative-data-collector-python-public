import pymongo
from pymongo.collection import Collection

from common.mongo_initializer import MONGO_URL

MONGO_DATABASE = 'france_scraping_recollect'
BILL_PAGES_COLLECTION_NAME = 'bill_pages'
LEG_RECORDS_COLLECTION_NAME = 'records'
SENATOR_PAGES_COLLECTION_NAME = 'senator_pages'
SENATORS_COLLECTION_NAME = 'senators'
AN_MEMBER_PAGES_COLLECTION_NAME = 'an_member_pages'
AN_MEMBERS_COLLECTION_NAME = 'an_members'
AMENDMENTS_COLLECTION_NAME = 'amendments'
LAW_TYPE_PAGES_COLLECTION = 'law_type_pages'
IMPACT_ASSESSMENT_TEXT_PDFS_COLLECTION_NAME = 'ia_text_pdfs'
BILL_TEXT_PDFS_COLLECTION_NAME = 'bill_text_pdfs'
AMENDMENT_TEXT_PDFS_COLLECTION_NAME = 'amendment_text_pdfs'

def get_collection(name) -> Collection:
    return pymongo.MongoClient(MONGO_URL)[MONGO_DATABASE].get_collection(name)


def get_bill_pages_collection() -> Collection:
    return get_collection(BILL_PAGES_COLLECTION_NAME)


def get_records_collection() -> Collection:
    return get_collection(LEG_RECORDS_COLLECTION_NAME)


def get_senator_pages_collection() -> Collection:
    return get_collection(SENATOR_PAGES_COLLECTION_NAME)


def get_senators_collection() -> Collection:
    return get_collection(SENATORS_COLLECTION_NAME)


def get_an_member_pages_collection() -> Collection:
    return get_collection(AN_MEMBER_PAGES_COLLECTION_NAME)


def get_an_members_collection() -> Collection:
    return get_collection(AN_MEMBERS_COLLECTION_NAME)


def get_amendments_collection() -> Collection:
    return get_collection(AMENDMENTS_COLLECTION_NAME)


def get_law_type_pages_collection() -> Collection:
    return get_collection(LAW_TYPE_PAGES_COLLECTION)


def get_ia_text_pdfs_collection() -> Collection:
    return get_collection(IMPACT_ASSESSMENT_TEXT_PDFS_COLLECTION_NAME)
def get_bill_text_pdfs_collection() -> Collection:
    return get_collection(BILL_TEXT_PDFS_COLLECTION_NAME)
def get_amendment_text_pdfs_collection() -> Collection:
    return get_collection(AMENDMENT_TEXT_PDFS_COLLECTION_NAME)
