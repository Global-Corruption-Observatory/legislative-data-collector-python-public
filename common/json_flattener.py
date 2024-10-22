import _csv
import datetime
import os

import pandas

COUNTRY = os.environ['COUNTRY']
if COUNTRY == 'fr':
    # FRENCH dataset:
    import france.mongo_initializer as mongo_initializer
elif COUNTRY == 'pt':
    # PORTUGAL dataset:
    import portugal.mongo_initializer as mongo_initializer
elif COUNTRY == 'ge':
    # GERMAN dataset:
    from germany import db_handler


records_collection = mongo_initializer.get_records_collection()

originator_columns = ['record_id', 'originator_name', 'originator_affiliation']
committees_columns = ['record_id', 'committee_name', 'committee_role', 'committee_date']
modified_laws_columns = ['record_id', 'modified_law_id', 'modified_record_id']
affecting_laws_columns = ['record_id', 'affecting_law_id', 'affecting_record_id']
stages_columns = ['record_id', 'number', 'name', 'date', 'house', 'debate_size']
amendments_columns = [
    'record_id', 'amendment_id', 'amendment_stage_name', 'amendment_stage_number', 'amendment_originator',
    'amendment_originator_aff', 'amendment_committee_name', 'amendment_text', 'amendment_text_url',
    'amendment_text_size', 'amendment_plenary', 'amendment_vote_for', 'amendment_vote_against', 'amendment_vote_abst',
    'amendment_outcome'
]
bill_main_table_columns = [
    'record_id', 'bill_page_url', 'bill_id', 'bill_title', 'bill_status', 'law_id', 'origin_type', 'bill_type',
    'date_introduction', 'date_committee', 'date_passing', 'date_entering_into_force', 'procedure_type_standard',
    'procedure_type_national', 'stages_count', 'plenary_size', 'committee_count', 'committee_hearing_count',
    'committee_hearing_count_external', 'committees_depth', 'modified_laws_count', 'affecting_laws_count',
    'affecting_laws_first_date', 'bill_text_url', 'bill_size', 'law_text_url', 'law_size', 'amendment_count',
    'ia_dummy', 'original_law', 'final_vote_for', 'final_vote_against', 'final_vote_abst'
]
bill_text_table_columns = ['record_id', 'bill_text']
law_text_table_columns = ['record_id', 'law_text']
impact_assessments_table_columns = [
    'record_id', 'ia_title', 'ia_text_url', 'ia_text', 'ia_size', 'ia_size1', 'ia_size2', 'ia_text1', 'ia_text2',
    'ia_date',
]

FILES_BASE_PATH = f'../data_handover/{COUNTRY}/{str(datetime.date.today())}'

if not os.path.exists(FILES_BASE_PATH):
    os.makedirs(FILES_BASE_PATH)

with open(f'{FILES_BASE_PATH}/originators.csv', 'w') as originators_file, \
        open(f'{FILES_BASE_PATH}/committees.csv', 'w') as committees_file, \
        open(f'{FILES_BASE_PATH}/modified_laws.csv', 'w') as modified_laws_file, \
        open(f'{FILES_BASE_PATH}/affecting_laws.csv', 'w') as affecting_laws_file, \
        open(f'{FILES_BASE_PATH}/legislative_stages.csv', 'w') as stages_file, \
        open(f'{FILES_BASE_PATH}/amendments.csv', 'w') as amendments_file, \
        open(f'{FILES_BASE_PATH}/bill_text.csv', 'w') as bill_text_file, \
        open(f'{FILES_BASE_PATH}/law_text.csv', 'w') as law_text_file, \
        open(f'{FILES_BASE_PATH}/impact_assessments.csv', 'w') as impact_assessments_file, \
        open(f'{FILES_BASE_PATH}/bill_main_table.csv', 'w') as bill_main_table_file:
    print('Exporting dataset to CSV...')

    originators_file.write(','.join(originator_columns) + '\n')
    committees_file.write(','.join(committees_columns) + '\n')
    modified_laws_file.write(','.join(modified_laws_columns) + '\n')
    affecting_laws_file.write(','.join(affecting_laws_columns) + '\n')
    stages_file.write(','.join(stages_columns) + '\n')
    amendments_file.write(','.join(amendments_columns) + '\n')
    bill_text_file.write(','.join(bill_text_table_columns) + '\n')
    law_text_file.write(','.join(law_text_table_columns) + '\n')
    impact_assessments_file.write(','.join(impact_assessments_table_columns) + '\n')
    bill_main_table_file.write(','.join(bill_main_table_columns) + '\n')

    # GERMAN dataset:
    # for rec in db_handler.get_records(filter={}):

    # PORTUGAL and FRENCH datasets:
    for rec in records_collection.find():
        try:
            originators_frame = pandas.json_normalize(
                rec, record_path=['originators'], meta=['record_id']).reindex(columns=originator_columns)
            committees_frame = pandas.json_normalize(
                rec, record_path=['committees'], meta=['record_id']).reindex(columns=committees_columns)
            modified_laws_frame = pandas.json_normalize(rec, record_path=['modified_laws'], meta=['record_id'])
            amendments_frame = pandas.json_normalize(
                rec, record_path=['amendments'], meta=['record_id']).reindex(columns=amendments_columns)
            stages_frame = pandas.json_normalize(
                rec, record_path=['legislative_stages'], meta=['record_id']).reindex(columns=stages_columns)
            bill_main_table_frame = pandas.json_normalize(rec).reindex(columns=bill_main_table_columns)
            bill_text_frame = pandas.json_normalize(rec).reindex(columns=bill_text_table_columns)
            law_text_frame = pandas.json_normalize(rec).reindex(columns=law_text_table_columns)
            impact_assessments_frame = pandas.json_normalize(rec).reindex(columns=impact_assessments_table_columns)

            # add record ID of modified laws
            if not modified_laws_frame.empty:
                modified_record_ids = []
                for i in range(0, len(modified_laws_frame[0])):
                    modified_law = modified_laws_frame[0][i]

                    if modified_record := records_collection.find_one({'law_id': modified_law}):
                        modified_record_ids.append(modified_record['record_id'])
                    else:
                        modified_record_ids.append(None)

                modified_laws_frame = modified_laws_frame.assign(modified_record_id=modified_record_ids)
                modified_laws_frame = modified_laws_frame.reindex(columns=['record_id', 0, 'modified_record_id'])
                modified_laws_file.write(modified_laws_frame.to_csv(header=False, index=False))

            if 'affecting_laws' in rec:
                affecting_law_ids = []
                affecting_laws_frame = pandas.json_normalize(rec, record_path=['affecting_laws'], meta=['record_id'])

                for affecting_law_record_id in affecting_laws_frame[0]:
                    if affecting_record := records_collection.find_one({'record_id': affecting_law_record_id}):
                        affecting_law_ids.append(affecting_record['law_id'])
                    else:
                        affecting_law_ids.append(None)

                affecting_laws_frame = affecting_laws_frame.assign(affecting_law_id=affecting_law_ids)
                affecting_laws_frame = affecting_laws_frame.reindex(columns=['record_id', 'affecting_law_id', 0])
                affecting_laws_file.write(affecting_laws_frame.to_csv(header=False, index=False))

            filtered_impact_assessments_frame = impact_assessments_frame[impact_assessments_frame['ia_text_url'].notnull()]
            filtered_law_text_frame = law_text_frame[law_text_frame['law_text'].notnull()]
            filtered_bill_text_frame = bill_text_frame[bill_text_frame['bill_text'].notnull()]

            originators_file.write(originators_frame.to_csv(header=False, index=False, columns=originator_columns))
            committees_file.write(committees_frame.to_csv(header=False, index=False, columns=committees_columns))
            stages_file.write(stages_frame.to_csv(header=False, index=False))
            amendments_file.write(amendments_frame.to_csv(header=False, index=False, columns=amendments_columns))
            bill_main_table_file.write(
                bill_main_table_frame.to_csv(header=False, index=False, columns=bill_main_table_columns))
            bill_text_file.write(
                filtered_bill_text_frame.to_csv(header=False, index=False, columns=bill_text_table_columns))
            law_text_file.write(filtered_law_text_frame.to_csv(header=False, index=False, columns=law_text_table_columns))
            impact_assessments_file.write(
                filtered_impact_assessments_frame.to_csv(header=False, index=False, columns=impact_assessments_table_columns))
        except (AttributeError, _csv.Error) as e:
            print(f"Failed to write out record: {rec['record_id']} - {rec['bill_page_url']}")
