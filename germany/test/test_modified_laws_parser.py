from unittest import TestCase

from germany import modified_laws_parser


class ModifiedLawsParserTest(TestCase):
    def test_180418(self):
        expected = {'8052-5', '2030-2-30', '2030-1-9', '51-1', '860-5', '2030-1', '2211-3', '800-28', '8251-10',
                    '8252-3', '860-1', '860-3', '85-5', '800-19-4', '800-24', '702-3', '7632-6', '8052-1'}

        result = modified_laws_parser.parse_from_pdf('https://dserver.bundestag.de/gm/18/180418.pdf')

        self.assertIsNotNone(result)
        self.assertSetEqual(expected, result)

    def test_140289(self):
        expected = {'2330-32', '2330-2', '2330-29', '2330-19', '2330-14', '2330-22/1', '105-20', '213-1', '2170-1',
                    '2330-8-3', '235-12', '400-2', '402-24-8', '402-24-8-1', '402-27', '453-12', '610-7', '611-1',
                    '830-2', '860-3', '860-7'}

        result = modified_laws_parser.parse_from_pdf('https://dserver.bundestag.de/gm/14/140289.pdf')

        self.assertIsNotNone(result)
        self.assertSetEqual(expected, result)

    def test_140407(self):
        expected = {'860-9-2', '111-1', '2121-1', '2121-2', '2122-1', '2122-5', '2123-1', '2124-8', '2124-11',
                    '2124-12', '2124-13', '2124-14', '2124-15', '2124-16', '2124-17', '2124-18', '2124-19', '2124-20',
                    '2129-29', '2170-1', '2211-3', '300-2', '303-1', '303-8', '320-1', '330-1', '4110-1', '424-5-1',
                    '610-10', '702-1', '7111-1', '7130-1', '7830-1', '830-2', '860-1', '860-3', '860-5', '860-7',
                    '860-9', '910-6', '911-1', '9240-1', '96-1', '2330-32'}

        result = modified_laws_parser.parse_from_pdf('https://dserver.bundestag.de/gm/14/140407.pdf')

        self.assertIsNotNone(result)
        self.assertSetEqual(expected, result)
