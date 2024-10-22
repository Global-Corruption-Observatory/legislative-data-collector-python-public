import re
from re import RegexFlag

FR_PDF_HEADER_REGEX = \
    'Disponible au format Acrobat\\s+\\(\\d+ Koctets\\)|Document "pastillé" au format PDF\s+\\(\\d+ Koctets\\)'
WHITESPACE_PATTERN = re.compile('\s')


def clean_text(text: str) -> str:
    # remove multiple empty lines
    if text:
        text = re.sub(FR_PDF_HEADER_REGEX, '', text, flags=RegexFlag.MULTILINE)
        return re.sub(pattern='[ \n]{3,}', repl='\n\n', string=text, flags=RegexFlag.MULTILINE).strip()


def get_length_without_whitespace(text: str) -> int:
    if text:
        return len(remove_whitespace(text))

    return 0


def remove_whitespace(text: str) -> str:
    if text:
        return WHITESPACE_PATTERN.sub('', text)

    return ''

