from unittest import TestCase

from common.record import BILL_STATUS_ONGOING, BILL_STATUS_PASSED, BILL_STATUS_REJECTED, ORIGIN_TYPE_MP, ORIGIN_TYPE_GOV
from germany import bill_page_parser


class TestBillPageParser(TestCase):
    def test_bill_289627(self):
        with open('static_files/test_bill_289627.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/strafrechts%C3%A4nderungsgesetz-ausweitung-und-versch%C3%A4rfung-des-straftatbestandes-der-abgeordnetenbestechung/289627?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=datum_ab&pos=1',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual('289627', result.bill_id)
            self.assertEqual('... Strafrechtsänderungsgesetz - Ausweitung und Verschärfung des Straftatbestandes der Abgeordnetenbestechung', result.bill_title)
            self.assertEqual(ORIGIN_TYPE_MP, result.origin_type)
            self.assertEqual('2022.07.14', result.date_introduction)
            self.assertEqual(True, result.ia_dummy)
            self.assertEqual('2022.07.14', result.ia_date)
            self.assertEqual(BILL_STATUS_ONGOING, result.bill_status)
            self.assertEqual('https://dserver.bundestag.de/btd/20/027/2002777.pdf', result.bill_text_url)
            self.assertEqual('Abgeordnetenbestechung; Strafrechtsänderungsgesetz - Abgeordneter; Mandat - Strafgesetzbuch', result.policy_area)
            self.assertEqual(0, len(result.committees))
            self.assertEqual(0, result.committee_count)
            self.assertEqual(0, result.committee_hearing_count)
            self.assertEqual(0, result.stages_count)
            self.assertEqual(0, len(result.legislative_stages))

            self.assertEqual(1, len(result.originators))
            self.assertEqual('Fraktion der AfD', result.originators[0].originator_name)
            self.assertEqual('Fraktion der AfD', result.originators[0].originator_affiliation)
            self.assertEqual('Bundestag - Recht', result.bill_type)

    def test_bill_287569(self):
        with open('static_files/test_bill_287569.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-einf%C3%BChrung-virtueller-hauptversammlungen-von-aktiengesellschaften-und-%C3%A4nderung-genossenschafts/287569?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=datum_ab&pos=35',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual('287569', result.bill_id)
            self.assertEqual('Gesetz zur Einführung virtueller Hauptversammlungen von Aktiengesellschaften und Änderung genossenschafts- sowie insolvenz- und restrukturierungsrechtlicher Vorschriften', result.bill_title)
            self.assertEqual('2022.05.10', result.date_introduction)
            self.assertEqual('2022.07.26', result.date_passing)
            self.assertEqual('2022.07.27', result.date_entering_into_force)
            self.assertEqual(BILL_STATUS_PASSED, result.bill_status)
            self.assertEqual(True, result.ia_dummy)
            self.assertEqual('2022.05.10', result.ia_date)
            self.assertEqual('https://dserver.bundestag.de/btd/20/017/2001738.pdf', result.bill_text_url)
            self.assertEqual('Medien, Kommunikation und Informationstechnik - Recht - Wirtschaft', result.bill_type)
            self.assertEqual('Genossenschaft; Gesellschaftsrecht; Gesetz zur Einführung virtueller Hauptversammlungen von Aktiengesellschaften und Änderung genossenschafts- sowie insolvenz- und restrukturierungsrechtlicher Vorschriften; Hauptversammlung; Insolvenzrecht; Telekonferenz; Unternehmenssanierung - Aktiengesellschaft; Aktienstimmrecht; Aktionär; COVID-19; Digitalisierung; Insolvenzverfahren; Kommanditgesellschaft auf Aktien - Genossenschaftsgesetz; Gesetz über Maßnahmen im Gesellschafts-, Genossenschafts-, Vereins-, Stiftungs- und Wohnungseigentumsrecht zur Bekämpfung der Auswirkungen der COVID-19-Pandemie; Insolvenzordnung; Sozialgesetzbuch X; Unternehmensstabilisierungs- und -restrukturierungsgesetz', result.policy_area)
            self.assertEqual(ORIGIN_TYPE_MP, result.origin_type)
            self.assertEqual('Rechtsausschuss', result.leading_committee_name)
            self.assertEqual('20/2653', result.final_version_printed_matter_id)

            self.assertEqual(4, result.stages_count)
            self.assertEqual(4, len(result.legislative_stages))

            self.assertEqual(1, result.legislative_stages[0].number)
            self.assertEqual('LOWER', result.legislative_stages[0].house)
            self.assertEqual('1. Beratung', result.legislative_stages[0].name)
            self.assertEqual('2022.05.12', result.legislative_stages[0].date)

            self.assertEqual(2, result.legislative_stages[1].number)
            self.assertEqual('LOWER', result.legislative_stages[1].house)
            self.assertEqual('2. Beratung', result.legislative_stages[1].name)
            self.assertEqual('2022.07.07', result.legislative_stages[1].date)

            self.assertEqual(3, result.legislative_stages[2].number)
            self.assertEqual('LOWER', result.legislative_stages[2].house)
            self.assertEqual('3. Beratung', result.legislative_stages[2].name)
            self.assertEqual('2022.07.07', result.legislative_stages[2].date)

            self.assertEqual(4, result.legislative_stages[3].number)
            self.assertEqual('UPPER', result.legislative_stages[3].house)
            self.assertEqual('Durchgang', result.legislative_stages[3].name)
            self.assertEqual('2022.07.08', result.legislative_stages[3].date)

            self.assertEqual(3, len(result.originators))
            self.assertEqual('Fraktion BÜNDNIS 90/DIE GRÜNEN', result.originators[0].originator_name)
            self.assertEqual('Fraktion BÜNDNIS 90/DIE GRÜNEN', result.originators[0].originator_affiliation)
            self.assertEqual('Fraktion der FDP', result.originators[1].originator_name)
            self.assertEqual('Fraktion der FDP', result.originators[1].originator_affiliation)
            self.assertEqual('Fraktion der SPD', result.originators[2].originator_name)
            self.assertEqual('Fraktion der SPD', result.originators[2].originator_affiliation)

            self.assertEqual(4, len(result.committees))
            self.assertEqual('Rechtsausschuss (federführend)', result.committees[0].committee_name)
            self.assertEqual('Lead', result.committees[0].committee_role)
            self.assertEqual('Ausschuss für Digitales', result.committees[1].committee_name)
            self.assertIsNone(result.committees[1].committee_role)
            self.assertEqual('Finanzausschuss', result.committees[2].committee_name)
            self.assertIsNone(result.committees[2].committee_role)
            self.assertEqual('Wirtschaftsausschuss', result.committees[3].committee_name)
            self.assertIsNone(result.committees[3].committee_role)

            self.assertEqual(1, result.committee_hearing_count)

    def test_bill_287574(self):
        with open('static_files/test_bill_287574.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-flexibilisierung-des-zinssatzes-bei-steuernachzahlungen-und-steuererstattungen/287574?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=datum_ab&pos=84',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual('287574', result.bill_id)
            self.assertEqual(
                'Gesetz zur Flexibilisierung des Zinssatzes bei Steuernachzahlungen und Steuererstattungen',
                result.bill_title)
            self.assertEqual('2022.05.10', result.date_introduction)
            self.assertEqual(BILL_STATUS_REJECTED, result.bill_status)
            self.assertEqual(True, result.ia_dummy)
            self.assertEqual('2022.05.10', result.ia_date)
            self.assertEqual('https://dserver.bundestag.de/btd/20/017/2001744.pdf', result.bill_text_url)
            self.assertEqual('Gesetz zur Flexibilisierung des Zinssatzes bei Steuernachzahlungen und Steuererstattungen; Steuererstattung; Steuernachforderung; Zins - Bundesverfassungsgericht; Gerichtsentscheidung - Abgabenordnung', result.policy_area)
            self.assertEqual('Öffentliche Finanzen, Steuern und Abgaben', result.bill_type)
            self.assertEqual(ORIGIN_TYPE_MP, result.origin_type)
            self.assertEqual('Finanzausschuss', result.leading_committee_name)

            self.assertEqual(1, len(result.originators))
            self.assertEqual('Fraktion der AfD', result.originators[0].originator_name)
            self.assertEqual('Fraktion der AfD', result.originators[0].originator_affiliation)

            self.assertEqual(2, result.stages_count)
            self.assertEqual(2, len(result.legislative_stages))

            self.assertEqual(1, result.legislative_stages[0].number)
            self.assertEqual('LOWER', result.legislative_stages[0].house)
            self.assertEqual('1. Beratung', result.legislative_stages[0].name)
            self.assertEqual('2022.05.12', result.legislative_stages[0].date)

            self.assertEqual(2, result.legislative_stages[1].number)
            self.assertEqual('LOWER', result.legislative_stages[1].house)
            self.assertEqual('2. Beratung', result.legislative_stages[1].name)
            self.assertEqual('2022.06.23', result.legislative_stages[1].date)

            self.assertEqual(2, len(result.committees))
            self.assertEqual(2, result.committee_count)

            self.assertEqual('Finanzausschuss (federführend)', result.committees[0].committee_name)
            self.assertEqual('Lead', result.committees[0].committee_role)
            self.assertEqual('2022.05.12', result.committees[0].committee_date)

            self.assertEqual('Haushaltsausschuss', result.committees[1].committee_name)
            self.assertEqual(None, result.committees[1].committee_role)
            self.assertEqual('2022.05.12', result.committees[1].committee_date)

            self.assertEqual(1, result.committee_hearing_count)

    def test_bill_285558(self):
        with open('static_files/test_bill_285558.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/elftes-gesetz-zur-%C3%A4nderung-des-zweiten-buches-sozialgesetzbuch/285558?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=datum_ab&pos=203',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual('285558', result.bill_id)
            self.assertEqual(
                'Elftes Gesetz zur Änderung des Zweiten Buches Sozialgesetzbuch',
                result.bill_title)
            self.assertEqual('2022.03.17', result.date_introduction)
            self.assertEqual('2022.06.22', result.date_passing)
            self.assertEqual('2022.07.01', result.date_entering_into_force)
            self.assertEqual(BILL_STATUS_PASSED, result.bill_status)
            self.assertEqual(True, result.ia_dummy)
            self.assertEqual('2022.03.17', result.ia_date)
            self.assertEqual('https://dserver.bundestag.de/brd/2022/0126-22.pdf', result.bill_text_url)
            self.assertEqual(
                'Grundsicherung für Arbeitsuchende; Moratorium; Sozialgesetzbuch II - Bundesverfassungsgericht; Garantiertes Mindesteinkommen; Gerichtsentscheidung; Regierungsprogramm; Sanktion <Sozialrecht> - Gesetz über die Entschädigung der Soldatinnen und Soldaten und zur Neuordnung des Soldatenversorgungsrechts',
                result.policy_area)
            self.assertEqual('Soziale Sicherung', result.bill_type)
            self.assertEqual(ORIGIN_TYPE_GOV, result.origin_type)
            self.assertEqual('Ausschuss für Arbeit, Integration und Sozialpolitik', result.leading_committee_name)
            self.assertEqual('20/1881', result.final_version_printed_matter_id)

            self.assertEqual(5, result.stages_count)
            self.assertEqual(5, len(result.legislative_stages))

            self.assertEqual(1, result.legislative_stages[0].number)
            self.assertEqual('UPPER', result.legislative_stages[0].house)
            self.assertEqual('1. Durchgang', result.legislative_stages[0].name)
            self.assertEqual('2022.04.08', result.legislative_stages[0].date)

            self.assertEqual(2, result.legislative_stages[1].number)
            self.assertEqual('LOWER', result.legislative_stages[1].house)
            self.assertEqual('1. Beratung', result.legislative_stages[1].name)
            self.assertEqual('2022.05.13', result.legislative_stages[1].date)

            self.assertEqual(3, result.legislative_stages[2].number)
            self.assertEqual('LOWER', result.legislative_stages[2].house)
            self.assertEqual('2. Beratung', result.legislative_stages[2].name)
            self.assertEqual('2022.05.19', result.legislative_stages[2].date)

            self.assertEqual(4, result.legislative_stages[3].number)
            self.assertEqual('LOWER', result.legislative_stages[3].house)
            self.assertEqual('3. Beratung', result.legislative_stages[3].name)
            self.assertEqual('2022.05.19', result.legislative_stages[3].date)

            self.assertEqual(5, result.legislative_stages[4].number)
            self.assertEqual('UPPER', result.legislative_stages[4].house)
            self.assertEqual('2. Durchgang', result.legislative_stages[4].name)
            self.assertEqual('2022.06.10', result.legislative_stages[4].date)

            self.assertTrue(len(result.originators) == 1)
            self.assertEqual('Bundesregierung', result.originators[0].originator_name)
            self.assertEqual('Bundesministerium für Arbeit und Soziales (federführend)', result.originators[0].originator_affiliation)

            self.assertEqual(7, len(result.committees))
            self.assertEqual(6, result.committee_count)
            self.assertEqual(3, result.committee_hearing_count)

            self.assertEqual(
                'Ausschuss für Arbeit, Integration und Sozialpolitik (federführend)',
                result.committees[0].committee_name)
            self.assertEqual('Lead', result.committees[0].committee_role)
            self.assertEqual('2022.03.17', result.committees[0].committee_date)

            self.assertEqual('Ausschuss für Arbeit und Soziales (federführend)', result.committees[1].committee_name)
            self.assertEqual('Lead', result.committees[1].committee_role)
            self.assertEqual('2022.05.13', result.committees[1].committee_date)

            self.assertEqual('Ausschuss für Familie, Senioren, Frauen und Jugend', result.committees[2].committee_name)
            self.assertEqual(None, result.committees[2].committee_role)
            self.assertEqual('2022.05.13', result.committees[2].committee_date)

            self.assertEqual('Haushaltsausschuss gemäß § 96 Geschäftsordnung BT', result.committees[3].committee_name)
            self.assertEqual(None, result.committees[3].committee_role)
            self.assertEqual('2022.05.13', result.committees[3].committee_date)

            self.assertEqual('Haushaltsausschuss', result.committees[4].committee_name)
            self.assertEqual(None, result.committees[4].committee_role)
            self.assertEqual('2022.05.13', result.committees[4].committee_date)

            self.assertEqual('Rechtsausschuss', result.committees[5].committee_name)
            self.assertEqual(None, result.committees[5].committee_role)
            self.assertEqual('2022.05.13', result.committees[5].committee_date)

            self.assertEqual(
                'Ausschuss für Arbeit, Integration und Sozialpolitik (federführend)',
                result.committees[6].committee_name)
            self.assertEqual('Lead', result.committees[6].committee_role)
            self.assertEqual('2022.05.20', result.committees[6].committee_date)

    def test_bill_68571(self):
        with open('static_files/test_bill_275937.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-modernisierung-des-k%C3%B6rperschaftsteuerrechts/275937?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&start=1000&rows=250&sort=datum_ab&pos=1008',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual(1, result.amendment_count)
            self.assertEqual(1, len(result.amendments))

            self.assertEqual('2021.05.19', result.amendments[0].amendment_date)
            self.assertEqual('LOWER', result.amendments[0].amendment_plenary)
            self.assertEqual(1, result.amendments[0].amendment_stage_number)
            self.assertEqual('1. Beratung', result.amendments[0].amendment_stage_name)
            self.assertEqual('Lisa Paus, MdB, BÜNDNIS 90/DIE GRÜNEN; Anja Hajduk, MdB, BÜNDNIS 90/DIE GRÜNEN', result.amendments[0].amendment_originator)
            self.assertEqual('Fraktion BÜNDNIS 90/DIE GRÜNEN', result.amendments[0].amendment_originator_aff)
            self.assertEqual(BILL_STATUS_REJECTED, result.amendments[0].amendment_outcome)
            self.assertEqual('https://dserver.bundestag.de/btd/19/298/1929857.pdf', result.amendments[0].amendment_text_url)

    def test_bill_288769(self):
        with open('static_files/test_bill_288769.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-regelung-der-suizidhilfe/288769?f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=datum_ab&pos=81',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertIsNotNone(result)
            self.assertEqual(2, result.amendment_count)
            self.assertEqual(2, len(result.amendments))

            self.assertEqual('2022.06.24', result.amendments[0].amendment_date)
            self.assertEqual('LOWER', result.amendments[0].amendment_plenary)
            self.assertEqual(1, result.amendments[0].amendment_stage_number)
            self.assertEqual('1. Beratung', result.amendments[0].amendment_stage_name)
            self.assertEqual('https://dip.bundestag.de/vorgang/suizidpr%C3%A4vention-st%C3%A4rken-und-selbstbestimmtes-leben-erm%C3%B6glichen/285690', result.amendments[0].amendment_page_link)

            self.assertEqual('2023.07.06', result.amendments[1].amendment_date)
            self.assertEqual('LOWER', result.amendments[1].amendment_plenary)
            self.assertEqual(2, result.amendments[1].amendment_stage_number)
            self.assertEqual('2. Beratung', result.amendments[1].amendment_stage_name)
            self.assertEqual('https://dip.bundestag.de/vorgang/suizidpr%C3%A4vention-st%C3%A4rken/301514', result.amendments[1].amendment_page_link)

    def test_bill_189729(self):
        with open('static_files/test_bill_189729.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-sicherung-der-kriegswaffenkontrolle-g-sig-10020399/189729?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&start=1750&rows=250&sort=basisdatum_ab&pos=1930',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertEqual('1985.05.14', result.ia_date)

    def test_bill_296239(self):
        with open('static_files/test_bill_296239.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/neuntes-gesetz-zur-%C3%A4nderung-des-regionalisierungsgesetzes/296239?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=basisdatum_ab&pos=15',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertEqual('296239', result.bill_id)
            self.assertEqual('Neuntes Gesetz zur Änderung des Regionalisierungsgesetzes', result.bill_title)

            self.assertEqual(1, result.amendment_count)
            self.assertEqual(1, len(result.amendments))
            self.assertEqual('20/6039', result.amendments[0].amendment_id)
            self.assertEqual('LOWER', result.amendments[0].amendment_plenary)
            self.assertEqual(1, result.amendments[0].amendment_stage_number)
            self.assertEqual('1. Beratung', result.amendments[0].amendment_stage_name)
            self.assertEqual('https://dserver.bundestag.de/btd/20/060/2006039.pdf', result.amendments[0].amendment_text_url)
            self.assertEqual('Mike Moncsek, MdB, AfD; Wolfgang Wiehle, MdB, AfD', result.amendments[0].amendment_originator)
            self.assertEqual('Fraktion der AfD', result.amendments[0].amendment_originator_aff)
            self.assertEqual(BILL_STATUS_REJECTED, result.amendments[0].amendment_outcome)

            self.assertEqual(5, result.committee_count)
            self.assertEqual(6, len(result.committees))

            self.assertEqual('Verkehrsausschuss (federführend)', result.committees[0].committee_name)
            self.assertEqual('Lead', result.committees[0].committee_role)
            self.assertEqual('2023.02.09', result.committees[0].committee_date)

            self.assertEqual('Ausschuss für Digitales', result.committees[1].committee_name)
            self.assertEqual(None, result.committees[1].committee_role)
            self.assertEqual('2023.02.09', result.committees[1].committee_date)

            self.assertEqual('Ausschuss für Wohnen, Stadtentwicklung, Bauwesen und Kommunen', result.committees[2].committee_name)
            self.assertEqual(None, result.committees[2].committee_role)
            self.assertEqual('2023.02.09', result.committees[2].committee_date)

            self.assertEqual('Haushaltsausschuss gemäß § 96 Geschäftsordnung BT', result.committees[3].committee_name)
            self.assertEqual(None, result.committees[3].committee_role)
            self.assertEqual('2023.02.09', result.committees[3].committee_date)

            self.assertEqual('Haushaltsausschuss', result.committees[4].committee_name)
            self.assertEqual(None, result.committees[4].committee_role)
            self.assertEqual('2023.02.09', result.committees[4].committee_date)

            self.assertEqual('Verkehrsausschuss (federführend)', result.committees[5].committee_name)
            self.assertEqual('Lead', result.committees[5].committee_role)
            self.assertEqual('2023.03.17', result.committees[5].committee_date)

    def test_bill_274767(self):
        with open('static_files/test_bill_274767.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-zur-st%C3%A4rkung-der-kontrolle-der-exekutive-durch-das-parlament/274767?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=basisdatum_ab&pos=100',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertEqual('274767', result.bill_id)
            self.assertEqual('Gesetz zur Stärkung der Kontrolle der Exekutive durch das Parlament (Exekutivkontrollgesetz - ExekutivkontrollG)', result.bill_title)
            self.assertIsNone(result.bill_status)

    def test_bill_290223(self):
        with open('static_files/test_bill_290223.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-%C3%BCber-die-feststellung-des-bundeshaushaltsplans-f%C3%BCr-das-haushaltsjahr-2023/290223?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&rows=250&sort=basisdatum_ab&pos=35',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertEqual('290223', result.bill_id)
            self.assertEqual('Gesetz über die Feststellung des Bundeshaushaltsplans für das Haushaltsjahr 2023 (Haushaltsgesetz 2023)', result.bill_title)

            self.assertEqual(5, result.stages_count)
            self.assertEqual(5, len(result.legislative_stages))

            self.assertEqual(1, result.legislative_stages[0].number)
            self.assertEqual('UPPER', result.legislative_stages[0].house)
            self.assertEqual('1. Durchgang', result.legislative_stages[0].name)
            self.assertEqual('2022.09.16', result.legislative_stages[0].date)

            self.assertEqual(2, result.legislative_stages[1].number)
            self.assertEqual('LOWER', result.legislative_stages[1].house)
            self.assertEqual('1. Beratung', result.legislative_stages[1].name)
            self.assertEqual('2022.09.06', result.legislative_stages[1].date)

            self.assertEqual(3, result.legislative_stages[2].number)
            self.assertEqual('LOWER', result.legislative_stages[2].house)
            self.assertEqual('2. Beratung', result.legislative_stages[2].name)
            self.assertEqual('2022.11.22', result.legislative_stages[2].date)

            self.assertEqual(4, result.legislative_stages[3].number)
            self.assertEqual('LOWER', result.legislative_stages[3].house)
            self.assertEqual('3. Beratung', result.legislative_stages[3].name)
            self.assertEqual('2022.11.25', result.legislative_stages[3].date)

            self.assertEqual(5, result.legislative_stages[4].number)
            self.assertEqual('UPPER', result.legislative_stages[4].house)
            self.assertEqual('2. Durchgang', result.legislative_stages[4].name)
            self.assertEqual('2022.12.16', result.legislative_stages[4].date)

    def test_bill_154026(self):
        with open('static_files/test_bill_154026.html', 'r') as file:
            page_obj = {
                'url': 'https://dip.bundestag.de/vorgang/gesetz-%C3%BCber-die-feststellung-des-bundeshaushaltsplans-f%C3%BCr-das-haushaltsjahr-1992/154026?f.typ=Vorgang&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen&f.vorgangstyp_p=05Gesetze%2C%20Rechtsnormen~Gesetzgebung&f.aktivitaetsart_p=01Antr%C3%A4ge%2C%20Gesetzentw%C3%BCrfe&start=1500&rows=250&sort=basisdatum_ab&pos=1733',
                'source': (file.read())
            }

            result = bill_page_parser.parse_page(page_obj)

            self.assertEqual('154026', result.bill_id)
            self.assertEqual('Gesetz über die Feststellung des Bundeshaushaltsplans für das Haushaltsjahr 1992 (Haushaltsgesetz 1992) (G-SIG: 12020138)', result.bill_title)

            self.assertEqual(5, result.stages_count)
            self.assertEqual(5, len(result.legislative_stages))

            self.assertEqual(1, result.legislative_stages[0].number)
            self.assertEqual('UPPER', result.legislative_stages[0].house)
            self.assertEqual('1. Durchgang', result.legislative_stages[0].name)
            self.assertEqual('1991.09.27', result.legislative_stages[0].date)
            self.assertEqual('https://dserver.bundestag.de/brp/634.pdf#P.351', result.legislative_stages[0].debate_url)

            self.assertEqual(2, result.legislative_stages[1].number)
            self.assertEqual('LOWER', result.legislative_stages[1].house)
            self.assertEqual('1. Beratung', result.legislative_stages[1].name)
            self.assertEqual('1991.09.03', result.legislative_stages[1].date)
            self.assertEqual('https://dserver.bundestag.de/btp/12/12036.pdf#P.2981', result.legislative_stages[1].debate_url)

            self.assertEqual(3, result.legislative_stages[2].number)
            self.assertEqual('LOWER', result.legislative_stages[2].house)
            self.assertEqual('2. Beratung', result.legislative_stages[2].name)
            self.assertEqual('1991.11.26', result.legislative_stages[2].date)
            self.assertEqual('https://dserver.bundestag.de/btp/12/12059.pdf#P.4885', result.legislative_stages[2].debate_url)

            self.assertEqual(4, result.legislative_stages[3].number)
            self.assertEqual('LOWER', result.legislative_stages[3].house)
            self.assertEqual('3. Beratung', result.legislative_stages[3].name)
            self.assertEqual('1991.11.29', result.legislative_stages[3].date)
            self.assertEqual('https://dserver.bundestag.de/btp/12/12062.pdf#P.5279', result.legislative_stages[3].debate_url)

            self.assertEqual(5, result.legislative_stages[4].number)
            self.assertEqual('UPPER', result.legislative_stages[4].house)
            self.assertEqual('2. Durchgang', result.legislative_stages[4].name)
            self.assertEqual('1991.12.19', result.legislative_stages[4].date)
            self.assertEqual('https://dserver.bundestag.de/brp/638.pdf#P.577', result.legislative_stages[4].debate_url)

