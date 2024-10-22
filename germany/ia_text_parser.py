import re

from common import pdf_parser

START_LABEL_1 = 'C. Alternativen\n'
END_LABEL_1 = 'D.'
START_2_REGEX = re.compile('Begründung\n')
END_2_REGEX = re.compile('II.|Besonderer Teil')


def parse_from_pdf(file_path: str) -> str:
    return parse_from_bill_text(pdf_parser.extract_from_file(file_path))


def parse_from_bill_text(bill_text: str) -> (str, str):
    ia_text_1, ia_text_2 = None, None

    if bill_text:
        start_index = bill_text.find(START_LABEL_1)

        if start_index != -1:
            end_index = bill_text[start_index:].find(END_LABEL_1)

            if end_index != -1:
                ia_text_1 = bill_text[start_index:start_index + end_index].strip()

        if start2_match := START_2_REGEX.search(bill_text):
            ia_text_2 = bill_text[start2_match.start():]

            if end2_match := END_2_REGEX.search(ia_text_2):
                ia_text_2 = ia_text_2[:end2_match.start()].strip()

    return ia_text_1, ia_text_2

