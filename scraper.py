"""Scrape the Memory of the World Library for books and download them."""
import os
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_doc(source_link):
    """Download the book from the source link."""
    # Extract the filename from the source link
    filename = source_link.split("/")[-1].replace("%20", " ")
    file_path = os.path.join("books", filename)

    # Create the 'books' directory if it doesn't exist
    if not os.path.exists("books/"):
        os.makedirs("books/")

    try:
        # Send a GET request to download the file
        r = requests.get(source_link, stream=True, timeout=10)
        r.raise_for_status()
        # Write the content to a file in chunks
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
        logging.info("Downloaded %s", source_link)
    except RequestException as e:
        logging.error("Error downloading %s - %s", source_link, str(e))

def scrape_library():
    """Scrape the Memory of the World Library for books."""
    # Set up headless Chrome browser options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    try:
        # Initialize the Chrome browser
        with webdriver.Chrome(options=options) as browser:
            # Loop through all pages of the library
            for page in range(1, 3315): # pages = 3315
                browser.get(f"https://library.memoryoftheworld.org/#/books?page={page}")
                html = browser.page_source
                soup = BeautifulSoup(html, features="html.parser")
                # Find all links on the page
                for link in soup.find_all('a'):
                    clean_link = link.get('href')
                    # Check if the link is a book link
                    if "//nikomas.memoryoftheworld.org/" in clean_link:
                        clean_link = clean_link.replace(" ", "%20")
                        clean_link = "https:" + clean_link
                        logging.info("Downloading %s", clean_link)
                        # Download the book
                        download_doc(clean_link)
            browser.quit()
    except WebDriverException as e:
        logging.error("Error scraping the library - %s", str(e))

if __name__ == "__main__":
    scrape_library()
