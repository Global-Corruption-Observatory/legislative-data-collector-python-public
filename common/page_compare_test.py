import requests
from selenium import webdriver

page = 'https://www.assemblee-nationale.fr/dyn/15/amendements/1765/CION_LOIS/CL1'

resp = requests.get(page)
with open('requests.html', 'w') as file:
    file.write(resp.text)

browser = webdriver.Chrome()
browser.get(page)
src = browser.page_source
with open('selenium.html', 'w') as file:
    file.write(src)

browser.close()
