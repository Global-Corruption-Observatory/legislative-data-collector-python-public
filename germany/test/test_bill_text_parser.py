from unittest import TestCase

from common import pdf_parser
from common.text_utils import get_length_without_whitespace
from germany import bill_text_parser


class TestBillTextParser(TestCase):
    def loosely_compare_text(self, expected, actual):
        self.assertAlmostEqual(
            first=get_length_without_whitespace(expected),
            second=get_length_without_whitespace(actual),
            delta=100
        )

    def test_bill_2004685(self):
        with open('static_files/bill_text_2004685_expected.txt') as expected:
            result = bill_text_parser.extract_bill_text(
                pdf_parser.extract_from_file('static_files/bill_text_2004685.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_2007669(self):
        with open('static_files/bill_text_2007669.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(
                pdf_parser.extract_from_file('static_files/bill_text_2007669.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_2001738(self):
        with open('static_files/bill_text_2001738.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(pdf_parser.extract_from_file('static_files/2001738.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_2002777(self):
        with open('static_files/bill_text_2002777.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(pdf_parser.extract_from_file('static_files/2002777.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_2006274(self):
        with open('static_files/bill_text_2006274.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(pdf_parser.extract_from_file('static_files/2006274.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_1600643(self):
        with open('static_files/bill_text_1600643.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(pdf_parser.extract_from_file('static_files/bill_text_1600643.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)

    def test_bill_1310788(self):
        with open('static_files/bill_text_1310788.pdf_expected_text.txt') as expected:
            result = bill_text_parser.extract_bill_text(pdf_parser.extract_from_file('static_files/bill_text_1310788.pdf'))

            self.assertIsNotNone(result)
            self.loosely_compare_text(expected.read(), result)
