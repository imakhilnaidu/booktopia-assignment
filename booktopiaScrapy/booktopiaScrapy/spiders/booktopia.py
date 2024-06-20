import os
import logging
import pandas as pd
from scrapy import Request, Spider

SEARCH_URL = "https://www.booktopia.com.au/_next/data/PeK-yQ3fK1Ey7VCsReKBQ/search.json?keywords={}"
PRODUCT_URL = "https://www.booktopia.com.au/_next/data/PeK-yQ3fK1Ey7VCsReKBQ{}.json"


class BookTopia(Spider):
    name = "booktopia"
    custom_settings = {
        "LOG_LEVEL": "INFO",
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_DEBUG": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 5,
        "DOWNLOAD_DELAY": 0.15,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 120,
    }
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
        'x-nextjs-data': '1'
    }

    def __init__(self, *args, **kwargs):
        super(BookTopia, self).__init__(*args, **kwargs)
        logging.basicConfig(
            filename='booktopia_spider.log',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

    def start_requests(self):
        try:
            # Getting file path for input_list.csv
            file_path = os.path.join(os.getcwd(), "booktopiaScrapy/files/input_list.csv")

            # Reading input_list.csv
            isbn_df = pd.read_csv(file_path)

            # Looping through the first 100 rows of input_list.csv
            for isbn in isbn_df["ISBN13"][100:150]:

                # Making a request to get the search url
                yield Request(SEARCH_URL.format(isbn), headers=self.headers, callback=self.parse,
                              errback=self.error_callback, cb_kwargs={"isbn": isbn})
        except Exception as e:
            self.logger.error(f"Got error at start request: {e}")

    # Function to parse the search url
    def parse(self, response, **kwargs):
        isbn = kwargs.get("isbn")
        try:
            response_data = response.json()

            # Getting the product url
            path = response_data.get("pageProps", {}).get("__N_REDIRECT", "")

            # Making a request to get the product url
            if path:
                yield Request(PRODUCT_URL.format(path), method="GET", headers=self.headers, callback=self.parse_product,
                              errback=self.error_callback, cb_kwargs={"isbn": isbn})
            else:
                self.logger.info(f"ISBN {isbn} not found")
                data = {
                    "ISBN - 13": isbn,
                    "Title of the Book": "book not found",
                    "Book Type": "-",
                    "Original Price": "-",
                    "Discounted Price": "-",
                    "ISBN - 10": "-",
                    "Author": "-",
                    "Published Date": "-",
                    "Publisher": "-",
                    "No. of Pages": "-",
                }
                yield data
        except Exception as e:
            self.logger.error(f"Got error at parse() - {e}")

    # Function to parse the product
    def parse_product(self, response, **kwargs):
        isbn = kwargs.get("isbn")
        try:
            response = response.json()
            product = response.get("pageProps", {}).get("product", {})
            authors = [contributor.get("name", "") for contributor in product.get("contributors", "")]
            data = {
                "ISBN - 13": isbn,
                "Title of the Book": product.get("displayName", ""),
                "Book Type": product.get("bindingFormat", ""),
                "Original Price": product.get("retailPrice", ""),
                "Discounted Price": product.get("salePrice", ""),
                "ISBN - 10": product.get("isbn10", ""),
                "Author": ",".join(authors),
                "Published Date": product.get("publicationDate", ""),
                "Publisher": product.get("publisher", ""),
                "No. of Pages": product.get("numberOfPages", ""),
            }
            yield data
        except Exception as e:
            self.logger.error(f"Got error at parse_product() - {e}")

    # Function to handle errors
    def error_callback(self, failure):
        isbn = failure.request.cb_kwargs.get("isbn")
        response = failure.value.response
        if response.status == 404:
            self.logger.info("Book not found")
            data = {
                "ISBN - 13": isbn,
                "Title of the Book": "book not found",
                "Book Type": "-",
                "Original Price": "-",
                "Discounted Price": "-",
                "ISBN - 10": "-",
                "Author": "-",
                "Published Date": "-",
                "Publisher": "-",
                "No. of Pages": "-",
            }
            yield data
