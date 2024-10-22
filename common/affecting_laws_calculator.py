from datetime import datetime

from common.date_utils import try_parse_date
from common.utils import format_date


def calculate_affecting_laws(records_collection):
    print('Calculating affecting laws...')

    modified_law_groups = records_collection.aggregate([
        {"$unwind": "$modified_laws"},
        {"$group": {"_id": "$modified_laws", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])

    for group in modified_law_groups:
        law_id = group['_id']
        count = group['count']

        affecting_laws = list(records_collection.find({'modified_laws': law_id}))
        affecting_record_ids = [law['record_id'] for law in affecting_laws]

        dates = [try_parse_date(law['date_passing']) for law in affecting_laws if law['date_passing'] is not None]

        earliest = format_date(min(dates)) if dates else None

        # todo add affecting laws field to the record class?
        update_result = records_collection.find_one_and_update(
            {'law_id': law_id},
            {"$set": {
                'affecting_laws_count': count, 'affecting_laws_first_date': earliest,
                'affecting_laws': affecting_record_ids
            }}
        )

        if update_result:
            print(f'Updated record: {update_result["record_id"]}')
