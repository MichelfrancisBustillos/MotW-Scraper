from bs4 import BeautifulSoup
from selenium import webdriver
import requests
import os

def download_doc(source_link):
    filename = source_link.split("/")[-1].replace("%20", " ")
    file_path = "books/" + filename
    
    if os.path.exists("books/"):
        pass
    else:
        os.makedirs("books/")

    r = requests.get(source_link, stream=True)
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
for pages in range(1, 2): # pages = 3315
    browser.get("https://library.memoryoftheworld.org/#/books?page=" + str(pages))
    html = browser.page_source
    soup = BeautifulSoup(html, features="html.parser")
    for link in soup.find_all('a'):
        source_link = link.get('href')
        if "//nikomas.memoryoftheworld.org/" in source_link:
            print(source_link)
            source_link = source_link.replace(" ", "%20")
            source_link = "https:" + source_link
            download_doc(source_link)
            
browser.quit()
