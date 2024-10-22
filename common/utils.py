import sys

import bs4
from bs4 import BeautifulSoup


def bs4_parse(page_src: str) -> BeautifulSoup:
    return bs4.BeautifulSoup(page_src, 'html.parser')


def clean_name(name):
    return name.replace('M.', '').replace('Mme', '').strip()


def print_error(msg):
    print(msg, file=sys.stderr)


def format_date(date):
    return date.strftime('%Y-%m-%d')
