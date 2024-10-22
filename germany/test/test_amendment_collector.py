from unittest import TestCase

from germany import amendment_collector


class Test(TestCase):
    def test_amendment_276861(self):
        with open('static_files/test_amendment_276861.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/thesaurierungsbeg%C3%BCnstigung-modernisieren/276861',
                'source': (file.read())
            }

            result: dict = amendment_collector.process_amendment_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual('276861', result.get('amendment_id'))
            self.assertEqual('REJECT', result.get('amendment_outcome'))
            self.assertEqual('https://dserver.bundestag.de/btd/19/287/1928766.pdf', result.get('amendment_text_url'))
            self.assertEqual('Katja Hessel, MdB, FDP; Christian Dürr, MdB, FDP', result.get('amendment_originator'))
            self.assertEqual('Fraktion der FDP', result.get('amendment_originator_aff'))

