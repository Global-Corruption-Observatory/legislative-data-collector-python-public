from pymongo.cursor import Cursor

from germany.mongo_initializer import *

QUERY_PARAMS = {
    'batch_size': 5, # fixes the cursor timeout errors
    'no_cursor_timeout': True,
    'allow_disk_use': True
}


def get_records(filter: dict) -> Cursor:
    return get_records_collection().find(filter=filter, **QUERY_PARAMS)


def get_bill_links() -> Cursor:
    return get_bill_links_collection().find(**QUERY_PARAMS)


def get_bill_pages() -> Cursor:
    return get_bill_pages_collection().find(**QUERY_PARAMS)


def get_vote_pdf_links() -> Cursor:
    return get_vote_pdf_links_collection().find(**QUERY_PARAMS)


def get_vote_pdfs() -> Cursor:
    return get_vote_pdfs_collection().find(**QUERY_PARAMS)

