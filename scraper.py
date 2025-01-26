"""Scrape the Memory of the World Library for books and download them."""
import os
from bs4 import BeautifulSoup
from selenium import webdriver
import requests

def download_doc(source_link):
    """Download the book from the source link."""
    filename = source_link.split("/")[-1].replace("%20", " ")
    file_path = "books/" + filename

    if os.path.exists("books/"):
        pass
    else:
        os.makedirs("books/")

    r = requests.get(source_link, stream=True, timeout=5)
    if r.ok:
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
    else:
        print("Failed to download " + source_link)

options = webdriver.ChromeOptions()
options.add_argument('--headless')
# executable_path param is not needed if you updated PATH
browser = webdriver.Chrome(options=options)
for pages in range(1, 3315): # pages = 3315
    browser.get("https://library.memoryoftheworld.org/#/books?page=" + str(pages))
    html = browser.page_source
    soup = BeautifulSoup(html, features="html.parser")
    for link in soup.find_all('a'):
        clean_link = link.get('href')
        if "//nikomas.memoryoftheworld.org/" in clean_link:
            clean_link = clean_link.replace(" ", "%20")
            clean_link = "https:" + clean_link
            print(clean_link)
            download_doc(clean_link)

browser.quit()
