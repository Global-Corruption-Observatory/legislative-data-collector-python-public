import logging
import re
import traceback
from datetime import datetime, date


def parse_date_expr(date_expr: str) -> date:
    month_translations = {
        'janvier': '01',
        'février': '02',
        'fevrier': '02',
        'mars': '03',
        'avril': '04',
        'mai': '05',
        'juin': '06',
        'juillet': '07',
        'août': '08',
        'septembre': '09',
        'octobre': '10',
        'novembre': '11',
        'décembre': '12',
        'decembre': '12',
    }

    for month in month_translations.keys():
        date_expr = date_expr.replace(month, month_translations[month])

    date_expr = date_expr.replace('1er', '1').lower()
    date_expr = re.sub('[^\\d\\s]', '', date_expr).strip() # remove weekday names

    date_components = date_expr.split(' ')

    try:
        return datetime(int(date_components[2]), int(date_components[1]), int(date_components[0])).date()
    except ValueError:
        logging.error(f'Can not parse date: {date_expr}')
        traceback.print_exc()


def try_parse_date(date_str):
    date_formats = ('%Y.%m.%d', '%Y-%m-%d')
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logging.warning('Can not parse date: %s' % date_str)
