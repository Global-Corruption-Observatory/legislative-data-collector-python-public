import logging

from common import affecting_laws_calculator
from germany import bill_page_parser, \
    modified_laws_parser, bill_link_collector, bill_page_downloader, amendment_collector, votes_collector, \
    mongo_initializer

# global logging settings
logging.basicConfig(format='%(asctime)s %(levelname)s %(thread)d %(message)s', level=logging.INFO)

# main steps of the collection
bill_link_collector.collect_links()
bill_page_downloader.download_pages()

bill_page_parser.parse_stored_pages()
bill_page_parser.download_bill_texts()
bill_page_parser.download_law_texts()
bill_page_parser.parse_ia_texts()

modified_laws_parser.collect_modified_laws()
affecting_laws_calculator.calculate_affecting_laws(mongo_initializer.get_records_collection())

amendment_collector.collect_amendment_pages()
amendment_collector.process_all_amendments()
amendment_collector.collect_amendment_texts()
amendment_collector.fix_amendment_houses()

votes_collector.fetch_pdf_links()
votes_collector.download_pdfs()
votes_collector.parse_pdfs()

bill_page_parser.collect_stage_debate_sizes()
