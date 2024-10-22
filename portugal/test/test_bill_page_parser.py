from unittest import TestCase

from common.record import BILL_STATUS_PASSED, BILL_STATUS_REJECTED, ORIGIN_TYPE_GOV, ORIGIN_TYPE_MP
from portugal import bill_page_parser


class TestBillPageParser(TestCase):
    def test_bill_151851_process_page(self):
        with open('static_files/test_bill_151851.html', 'r') as file:
            stored_page = {
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=151851',
                'content_box_source': (file.read())
            }

            result = bill_page_parser.process_page(stored_page)

            self.assertIsNotNone(result)
            self.assertEqual('33/XV/1', result.bill_id)
            self.assertEqual(
                'Determina o coeficiente de atualização de rendas para 2023, cria um apoio extraordinário ao '
                'arrendamento, reduz o IVA no fornecimento de eletricidade e estabelece um regime transitório de '
                'atualização das pensões',
                result.bill_title)
            self.assertEqual(ORIGIN_TYPE_GOV, result.origin_type)
            self.assertEqual('2022-09-05', result.date_introduction)
            self.assertEqual('2022-09-12', result.date_committee)
            self.assertEqual(BILL_STATUS_PASSED, result.bill_status)
            self.assertEqual('2022-10-21', result.date_passing)

            self.assertEqual(19, result.stages_count)
            self.assertEqual(19, len(result.legislative_stages))
            self.assertEqual({'date': '2022-09-05', 'name': 'Entrada'}, result.legislative_stages[0])
            self.assertEqual({'date': '2022-10-21', 'name': 'Lei (Publicação DR)'}, result.legislative_stages[18])

            self.assertEqual(1, result.committee_count)
            self.assertEqual(1, len(result.committees))
            self.assertEqual({'committee_name': 'Comissão de Orçamento e Finanças'}, result.committees[0])

            self.assertEqual(
                'https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356c6443397a6158'
                '526c63793959566b786c5a79394562324e31625756756447397a5357357059326c6864476c32595338334d6d4977595746684d'
                '6931695a6a45794c5451774f5749744f54646d5a53316c4d4459335a54686a5a544669593251755a47396a&fich=72b0aaa2-'
                'bf12-409b-97fe-e067e8ce1bcd.doc&Inline=true',
                result.bill_text_url)
            self.assertEqual(6407, result.bill_size)

            self.assertEqual(True, result.ia_dummy)
            self.assertEqual('Avaliação Prévia de Impacto de Género', result.ia_title)
            self.assertEqual(8289, result.ia_size)

            self.assertEqual('PS,  CH', result.final_vote_for)
            self.assertEqual('PSD,  IL,  PCP,  BE', result.final_vote_against)
            self.assertEqual('PAN,  L', result.final_vote_abst)

    def test_bill_121494_process_page(self):
        with open('static_files/test_bill_121494.html', 'r') as file:
            stored_page = {
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=121494',
                'content_box_source': (file.read())
            }

            result = bill_page_parser.process_page(stored_page)

            self.assertIsNotNone(result)
            self.assertEqual('94/XV/1', result.bill_id)
            self.assertEqual(
                'Criação do Estatuto do Arguido Colaborador e agravamento das penas aplicáveis aos crimes de '
                'corrupção previstos no Código Penal',
                result.bill_title)
            self.assertEqual(ORIGIN_TYPE_MP, result.origin_type)
            self.assertEqual('2022-05-20', result.date_introduction)
            self.assertEqual('2022-05-24', result.date_committee)
            self.assertEqual(BILL_STATUS_REJECTED, result.bill_status)
            self.assertIsNone(result.date_passing)

            self.assertEqual(7, result.stages_count)
            self.assertEqual(7, len(result.legislative_stages))

            self.assertEqual({'date': '2022-05-20', 'name': 'Publicação'}, result.legislative_stages[0])
            self.assertEqual({'date': '2022-06-03', 'name': 'Votação na generalidade'}, result.legislative_stages[6])

            self.assertEqual(1, result.committee_count)
            self.assertEqual(1, len(result.committees))
            self.assertEqual(
                {'committee_name': 'Comissão de Assuntos Constitucionais, Direitos, Liberdades e Garantias'},
                result.committees[0])

            self.assertEqual(
                'https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356c6443397a6158'
                '526c63793959566b786c5a79394562324e31625756756447397a5357357059326c6864476c32595338314f4467304d7a45775a'
                '4331694d5759344c5451354d54517459544d78595330794d4759774d7a517a4d6a4a6b4d7a63755a47396a&fich=5884310d-'
                'b1f8-4914-a31a-20f034322d37.doc&Inline=true',
                result.bill_text_url)
            self.assertEqual(10302, result.bill_size)

            self.assertEqual('Avaliação Prévia de Impacto de Género', result.ia_title)
            self.assertEqual(
                'https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356c6443397a6158'
                '526c63793959566b786c5a79394562324e31625756756447397a5357357059326c6864476c32595338784d6d4933597a557a59'
                '69316a4e6a526d4c5451334f4441744f544d304e533033595463304e7a59794d6a466b595451756347526d&fich=12b7c53b-'
                'c64f-4780-9345-7a7476221da4.pdf&Inline=true',
                result.ia_text_url)
            self.assertEqual(7871, result.ia_size)

            self.assertEqual('CH', result.final_vote_for)
            self.assertEqual('PS,  PSD,  PCP,  BE,  L', result.final_vote_against)
            self.assertEqual('IL,  PAN', result.final_vote_abst)

    def test_bill_110576_process_page(self):
        with open('static_files/test_bill_110576.html', 'r') as file:
            stored_page = {
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=110576',
                'content_box_source': (file.read())
            }

            result = bill_page_parser.process_page(stored_page)

            self.assertIsNotNone(result)
            self.assertEqual('757/XIV/2', result.bill_id)
            self.assertEqual(
                'Reforça a participação política dos grupos de cidadãos eleitores',
                result.bill_title)
            self.assertEqual(ORIGIN_TYPE_MP, result.origin_type)
            self.assertEqual('2021-03-25', result.date_introduction)
            self.assertEqual('2021-03-26', result.date_committee)
            self.assertEqual('2021-06-04', result.date_passing)

            self.assertEqual(25, result.stages_count)
            self.assertEqual(25, len(result.legislative_stages))
            self.assertEqual(47492, result.plenary_size)

            self.assertEqual(1, result.committee_count)
            self.assertEqual(4, result.committee_hearing_count_external)
            self.assertEqual({'committee_name': 'Comissão de Assuntos Constitucionais, Direitos, Liberdades e'
                                                ' Garantias'}, result.committees[0])

            self.assertEqual(
                'https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356c6443397a6158'
                '526c6379395953565a4d5a5763765247396a6457316c626e527663306c7561574e7059585270646d45764f5451774d32557a4e'
                '6d4d74596a5a6d4f5330304e7a4e684c5467354e7a4d744d6a46694d57466b4e6d5131596d4e6a4c6d527659773d3d&fich='
                '9403e36c-b6f9-473a-8973-21b1ad6d5bcc.doc&Inline=true',
                result.bill_text_url)
            self.assertEqual(9112, result.bill_size)
            self.assertEqual('https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356'
                             'c6443397a6158526c6379395953565a4d5a5763765247396a6457316c626e527663306c7561574e7059585270'
                             '646d4576593249305954466b4f4459744d546b7a4e533030595745314c574a684e4455744e5759324f44466d5'
                             '9324e69595759354c6e426b5a673d3d&fich=cb4a1d86-1935-4aa5-ba45-5f681fccbaf9.pdf&Inline=true'
                             , result.ia_text_url)

            self.assertEqual('104-PS,  18-BE,  5-CDS-PP,  2-PAN,  Cristina Rodrigues (Ninsc),  '
                             'Joacine Katar Moreira (Ninsc)', result.final_vote_for)
            self.assertEqual('75-PSD,  10-PCP,  2-PEV', result.final_vote_against)
            self.assertEqual('1-CH,  1-IL', result.final_vote_abst)

    def test_bill_151851(self):
        with open('static_files/test_bill_151851.html', 'r') as file:
            stored_page = {
                '_id': '',
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=151851',
                'content_box_source': (file.read())
            }

            record = bill_page_parser.process_page(stored_page)
            bill_page_parser.process_law_variables(record, stored_page)

            self.assertEqual(BILL_STATUS_PASSED, record.bill_status)
            self.assertEqual('19/2022', record.law_id)
            self.assertEqual('2022-10-21', record.date_passing)
            self.assertEqual('2022-10-22', record.date_entering_into_force)
            self.assertEqual(7880, record.law_size)
            self.assertEqual('https://app.parlamento.pt/webutils/docs/doc.pdf?path=6148523063484d364c793968636d356'
                             'c6443397a6158526c63793959566b786c5a79394562324e31625756756447397a51574e3061585a705a47466b'
                             '5a564268636d786862575675644746794c7a5a694d4455335a6a526c4c574d7a5a6a6b744e4449325a4331694'
                             'e6a59304c5749305a44686d4e5463315a444d344f4335775a47593d&fich=6b057f4e-c3f9-426d-b664-'
                             'b4d8f575d388.pdf&Inline=true', record.law_text_url)
            self.assertEqual(True, record.original_law)

    def test_bill_151998(self):
        with open('static_files/test_bill_151998.html', 'r') as file:
            stored_page = {
                '_id': '',
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=151998',
                'content_box_source': (file.read())
            }

            record = bill_page_parser.process_page(stored_page)
            bill_page_parser.process_law_variables(record, stored_page)

            self.assertEqual(BILL_STATUS_PASSED, record.bill_status)
            self.assertEqual('20/2023', record.law_id)
            self.assertEqual('2023-05-17', record.date_passing)

    def test_bill_233252(self):
        with open('static_files/test_bill_233252.html', 'r') as file:
            stored_page = {
                '_id': '',
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=233252',
                'content_box_source': (file.read())
            }

            record = bill_page_parser.process_page(stored_page)
            bill_page_parser.process_law_variables(record, stored_page)

            self.assertEqual(BILL_STATUS_PASSED, record.bill_status)
            self.assertEqual('60-A/2023', record.law_id)
            self.assertEqual('2023-10-31', record.date_passing)
            self.assertEqual(1, record.modified_laws_count)
            self.assertEqual(False, record.original_law)

    def test_bill_173077(self):
        with open('static_files/test_bill_173077.html', 'r') as file:
            stored_page = {
                '_id': '',
                'url': 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=173077',
                'content_box_source': (file.read())
            }

            record = bill_page_parser.process_page(stored_page)
            bill_page_parser.process_law_variables(record, stored_page)

            self.assertEqual(BILL_STATUS_PASSED, record.bill_status)
            self.assertEqual('62/2023', record.law_id)
            self.assertEqual('2023-11-09', record.date_passing)
            self.assertEqual(1, record.modified_laws_count)
            self.assertEqual(False, record.original_law)
