import re

START_LABEL = 'Artikel 1\n'
END_LABEL = 'Besonderer Teil'

# start label could be (don't include this in the bill text):
#   Der Bundestag hat das folgende Gesetz beschlossen:
#   Der Bundestag hat mit Zustimmung des Bundesrates das folgende Gesetz beschlossen:
#   Artikel 1
#
# end label could be: Begründung? (not part of the law text)


def extract_bill_text(full_pdf_text: str) -> str:
    bill_text = full_pdf_text

    if bill_text:
        # replace double spaces with single space
        clean_text = re.sub(' +', ' ', bill_text)

        if (start_index := clean_text.find(START_LABEL)) != -1:
            bill_text = clean_text[start_index:]

            if (end_index := bill_text.find(END_LABEL)) != -1:
                bill_text = bill_text[:end_index]

        bill_text = bill_text.strip()

    return bill_text
