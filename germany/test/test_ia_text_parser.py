from unittest import TestCase

from common.text_utils import get_length_without_whitespace
from germany import ia_text_parser


class TestIaTextParser(TestCase):
    def loosely_compare_text(self, expected, actual):
        self.assertAlmostEqual(
            first=get_length_without_whitespace(expected),
            second=get_length_without_whitespace(actual),
            delta=100
        )

    def test_parse_from_pdf_1(self):
        with open('static_files/bill_248388_text.pdf.expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/bill_248388_text.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)

    def test_parse_from_pdf_2(self):
        with open('static_files/2001738.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/2001738.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)

    def test_parse_from_pdf_3(self):
        with open('static_files/2002777.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/2002777.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)


    def test_parse_from_pdf_4(self):
        with open('static_files/2006274.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/2006274.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)


    def test_parse_from_pdf_5(self):
        with open('static_files/2003939.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/2003939.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)


    def test_parse_from_pdf_6(self):
        with open('static_files/1708377.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/1708377.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)


    def test_parse_from_pdf_7(self):
        with open('static_files/2001540.pdf_expected_ia_text.txt', 'r') as exp:
            expected = exp.read()
            actual1, actual2 = ia_text_parser.parse_from_pdf('static_files/2001540.pdf')

            self.assertIsNotNone(actual1)
            self.assertIsNotNone(actual2)

            self.loosely_compare_text(expected, actual1 + actual2)

