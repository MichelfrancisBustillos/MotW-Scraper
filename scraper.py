"""Scrape the Memory of the World Library for books and download them."""
import os
import logging
import argparse
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import requests
from requests.exceptions import RequestException

# Configure logging to output to a file and the terminal
log_filename = datetime.now().strftime("scraper_%Y%m%d_%H%M%S.log")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_filename),
                        logging.StreamHandler()
])

def download_book(source_link, dryrun, scrape_counters, download_folder):
    """Download the book from the source link."""
    if dryrun:
        logging.info("Dry run, Skipping %s", source_link)
        return

    # Extract the filename from the source link
    filename = source_link.split("/")[-1].replace("%20", " ")
    file_path = os.path.join(download_folder, filename)

    # Create the download folder if it doesn't exist
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

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
        scrape_counters['total_books_downloaded'] += 1
    except RequestException as e:
        logging.error("Error downloading %s - %s", source_link, str(e))
        scrape_counters['error_count'] += 1

def scrape_library(dryrun, download_folder):
    """Scrape the Memory of the World Library for books."""
    scrape_counters = {
        'total_books_found': 0,
        'total_books_downloaded': 0,
        'error_count': 0
    }

    # Set up headless Chrome browser options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    try:
        # Initialize the Chrome browser
        with webdriver.Chrome(options=options) as browser:
            page = 1
            links_to_download = []
            while True:
                # Log the current page number being scraped
                logging.info("Scraping page %d", page)
                # Load the page
                browser.get(f"https://library.memoryoftheworld.org/#/books?page={page}")
                html = browser.page_source
                soup = BeautifulSoup(html, features="html.parser")
                links_found = False
                # Find all links on the page
                for link in soup.find_all('a'):
                    clean_link = link.get('href')
                    # Check if the link is a book link
                    if "//nikomas.memoryoftheworld.org/" in clean_link:
                        clean_link = "https:" + clean_link.replace(" ", "%20")
                        logging.info("Found %s", clean_link)
                        links_to_download.append(clean_link)
                        links_found = True
                if not links_found:
                    break
                page += 1
                # Rate limiting to avoid rejected connections
                time.sleep(random.randint(1, 5))
            browser.quit()

            scrape_counters['total_books_found'] = len(links_to_download)

            # Download all found links using threading
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(lambda link: download_book(link,
                                                        dryrun,
                                                        scrape_counters,
                                                        download_folder),
                             links_to_download)
    except WebDriverException as e:
        logging.error("Error scraping the library - %s", str(e))

    return scrape_counters

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape the Memory of the World Library for books and download them."
    )
    parser.add_argument('--dryrun',
                        action='store_true',
                        help="Get all download links but do not download the files.")
    parser.add_argument('--path',
                        type=str,
                        default='books',
                        help="Folder path to download books to.")
    args = parser.parse_args()

    if args.dryrun:
        logging.info("Running in dry run mode. No files will be downloaded.")

    counters = scrape_library(dryrun=args.dryrun, download_folder=args.path)

    # Log summary
    logging.info("Total books found: %d", counters['total_books_found'])
    logging.info("Total books downloaded: %d", counters['total_books_downloaded'])
    logging.info("Total errors: %d", counters['error_count'])
