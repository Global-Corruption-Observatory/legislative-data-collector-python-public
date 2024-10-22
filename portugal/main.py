import logging

from selenium import webdriver

from common import affecting_laws_calculator
from portugal import bill_page_downloader, bill_page_parser, mongo_initializer

window1 = webdriver.Chrome()
window2 = webdriver.Chrome()

# global logging settings
logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

# main steps of the collection
try:
    bill_page_downloader.download_bills(window1, window2)
    bill_page_downloader.download_committee_pages(window1, window2)
finally:
    window1.close()
    window2.close()

bill_page_parser.parse_bills()
affecting_laws_calculator.calculate_affecting_laws(mongo_initializer.get_records_collection())
bill_page_parser.fill_amendments()
bill_page_parser.set_bill_types()
