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
from fake_useragent import UserAgent
from tqdm import tqdm

def pretty_sleep(seconds, fast_mode):
    """Sleep for the input amount of time with a progress bar, unless fast mode is enabled."""
    if fast_mode:
        return
    for _i in tqdm(range(seconds), desc="Cooldown", unit="s", unit_scale=True):
        time.sleep(1)

def configure_logging(silent_mode, verbosity):
    """Configure logging to output to a file and optionally to the terminal."""
    log_filename = datetime.now().strftime("scraper_%Y%m%d_%H%M%S.log")
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    handlers = [file_handler]

    if not silent_mode:
        stream_handler = logging.StreamHandler()
        handlers.append(stream_handler)

    if verbosity == 1:
        file_handler.setLevel(logging.INFO)
        stream_handler.setLevel(logging.INFO)
    elif verbosity >= 2:
        file_handler.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
        stream_handler.setLevel(logging.ERROR)

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=handlers)

    logging.info("Log level set to %s for file and %s for terminal.",
                 logging.getLevelName(file_handler.level),
                 logging.getLevelName(stream_handler.level))

def download_book(source_link, dryrun, scrape_counters, download_folder, fast_mode):
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
        try:
            r = requests.get(source_link, stream=True, timeout=10)
        except WebDriverException as e:
            logging.error("Connection rejected. %s", str(e))
            logging.info("Cooldown for 1 minute due to connection rejection.")
            pretty_sleep(60, fast_mode)
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

def scrape_library(dryrun, download_folder, fast_mode):
    """Scrape the Memory of the World Library for books."""
    scrape_counters = {
        'total_books_found': 0,
        'total_books_downloaded': 0,
        'error_count': 0
    }

    # Set up headless Chrome browser options
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("user-agent=" + headers['User-Agent'])
    try:
        # Initialize the Chrome browser
        with webdriver.Chrome(options=options) as browser:
            page = 1
            links_to_download = []
            while True:
                # Log the current page number being scraped
                logging.info("Scraping page %d", page)
                # Load the page
                try:
                    browser.get(f"https://library.memoryoftheworld.org/#/books?page={page}")
                    logging.info("Page loaded successfully.")
                except WebDriverException as e:
                    logging.error("Connection rejected on page %d - %s", page, str(e))
                    logging.info("Cooldown for 1 minute due to connection rejection.")
                    pretty_sleep(60, fast_mode)
                    continue
                html = browser.page_source
                logging.info("Parsing page %d", page)
                soup = BeautifulSoup(html, features="html.parser")
                logging.info("Finding links on page %d", page)
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
                        scrape_counters['total_books_found'] = len(links_to_download)
                if not links_found:
                    logging.info("No more links found on page %d. Exiting...", page)
                    break
                page += 1
                # Rate limiting to avoid rejected connections
                pretty_sleep(random.randint(10, 20), fast_mode)

            # Download all found links using threading
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(lambda link: download_book(link,
                                                        dryrun,
                                                        scrape_counters,
                                                        download_folder,
                                                        fast_mode),
                             links_to_download)
    except WebDriverException as e:
        logging.error("Error scraping the library - %s", str(e))

    browser.quit()
    return scrape_counters

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape the Memory of the World Library for books and download them."
    )
    parser.add_argument('--dryrun',
                        action='store_true',
                        help="Get all download links but do not download the files.")
    parser.add_argument('--path', '-p',
                        type=str,
                        default='books',
                        help="Folder path to download books to.")
    parser.add_argument('--fast', '-f',
                        action='store_true',
                        help="Disable all cooldowns for faster scraping.")
    parser.add_argument('--silent', '-s',
                        action='store_true',
                        help="Disable logging output to the terminal.")
    parser.add_argument('--verbose', '-v',
                        action='count',
                        default=0,
                        help="Increase verbosity level (can be used multiple times).")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    if '--help' not in args:
        configure_logging(silent_mode=args.silent, verbosity=args.verbose)

    if args.dryrun:
        logging.info("Running in dry run mode. No files will be downloaded.")

    try:
        counters = scrape_library(dryrun=args.dryrun,
                                  download_folder=args.path,
                                  fast_mode=args.fast)
        # Log summary
        logging.info("Total books found: %d", counters['total_books_found'])
        logging.info("Total books downloaded: %d", counters['total_books_downloaded'])
        logging.info("Total errors: %d", counters['error_count'])
    except KeyboardInterrupt:
        logging.info("Program interrupted by user. Exiting...")
