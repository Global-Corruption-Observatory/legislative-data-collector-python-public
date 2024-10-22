from dataclasses import dataclass


ORIGIN_TYPE_GOV: str = 'GOVERNMENT'
ORIGIN_TYPE_MP: str = 'INDIVIDUAL_MP'

BILL_STATUS_PASSED = 'PASS'
BILL_STATUS_REJECTED = 'REJECT'
BILL_STATUS_EXPIRED = 'EXPIRED'
BILL_STATUS_WITHDRAWN = 'WITHDRAWN'
BILL_STATUS_ONGOING = 'ONGOING'


@dataclass
class Committee:
    committee_name: str = None
    committee_role: str = None
    committee_date: str = None


@dataclass
class Originator:
    originator_name: str = None
    originator_affiliation: str = None


@dataclass
class Stage:
    number: int = None
    name: str = None
    date: str = None
    house: str = None
    debate_size: int = None
    debate_url: str = None


@dataclass
class Amendment:
    amendment_id: str = None
    amendment_stage_name: str = None
    amendment_stage_number: int = None
    amendment_date: str = None
    amendment_plenary: str = None
    amendment_originator: str = None
    amendment_originator_aff: str = None
    amendment_committee: str = None
    amendment_text_url: str = None
    amendment_text: str = None
    amendment_text_size: int = None
    amendment_outcome: str = None
    amendment_vote_for: str = None
    amendment_vote_against: str = None
    amendment_vote_abst: str = None
    amendment_page_link: str = None


@dataclass
class Record:
    record_id: str = None
    country: str = None
    bill_page_url: str = None
    bill_id: str = None
    bill_title: str = None
    original_law: bool = None
    bill_status: str = BILL_STATUS_ONGOING
    law_id: str = None
    origin_type: str = None
    originators: list = None
    bill_type: str = None
    date_introduction: str = None
    date_committee: str = None
    date_passing: str = None
    date_entering_into_force: str = None
    procedure_type_standard: str = None
    procedure_type_national: str = None
    legislative_stages: list = None
    stages_count: int = None
    plenary_size: int = None
    committees: list = None
    committee_count: int = None
    committee_hearing_count: int = None
    committees_depth: int = None
    modified_laws: list = None
    modified_laws_count: int = None
    affecting_laws_count: int = None
    affecting_laws_first_date: str = None
    bill_text_url: str = None
    bill_size: int = None
    bill_text: str = None
    law_text_url: str = None
    law_size: int = None
    law_text: str = None
    amendments: list = None
    amendment_count: int = None
    amendment_links: list = None
    ia_dummy: bool = None
    ia_title: str = None
    ia_text_url: str = None
    ia_text: str = None
    ia_date: str = None
    ia_size: int = None
    final_vote_for: int = None
    final_vote_against: int = None
    final_vote_abst: int = None

    # country specific - PT
    committee_hearing_count_external: int = None

    # country specific - FR
    law_text_footer: str = None

    # country specific - DE
    modified_laws_pdf_url: str = None
    origin_type_detail: str = None
    policy_area: str = None
    leading_committee_name: str = None
    final_version_printed_matter_id: str = None
    final_votes_pdf_url: str = None
    ia_text1: str = None
    ia_text2: str = None
    ia_size1: int = None
    ia_size2: int = None

