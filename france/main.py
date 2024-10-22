# global logging settings
import logging

from france import bill_page_downloader, an_members_page_downloader, an_members_page_parser, senators_page_downloader, \
    senator_page_parser, bill_page_parser, amendments_csv_downloader

logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

# main steps of the collection and parsing
bill_page_downloader.collect_bill_pages()
an_members_page_downloader.get_pages()
an_members_page_parser.parse_source()
senators_page_downloader.get_pages()
senator_page_parser.parse_source()
bill_page_parser.run_bill_page_parser()
amendments_csv_downloader.run_amendments_csv_downloader()
