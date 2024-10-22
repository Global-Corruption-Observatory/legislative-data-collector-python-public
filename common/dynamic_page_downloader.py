from selenium import webdriver


def get_page_source(page_url):
    browser = webdriver.Chrome()
    browser.get(page_url)
    src = browser.page_source

    browser.close()

    return src
