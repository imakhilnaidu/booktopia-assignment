import os
import re
import logging
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from time import sleep
from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PlaywrightTimeoutError


def run(playwright: Playwright, url: str, isbn_df):
    browser = playwright.chromium.launch()
    context = browser.new_context()

    # All Selectors
    title_selector = "h1[class='MuiTypography-root MuiTypography-h1 mui-style-1ngtbwk']"
    author_selector = "p[class='MuiTypography-root MuiTypography-body1 mui-style-snzs7y']"
    book_type_selector = "h3[class='MuiTypography-root MuiTypography-h3 mui-style-lijwn']"
    original_price_selector = "#BuyBox_product-version__uw1et p > .strike"
    discounted_price_selector = "p[class='MuiTypography-root MuiTypography-body1 BuyBox_sale-price__PWbkg mui-style-tgrox']"
    details_tab_selector = "button[id='pdp-tab-details']"
    details_section_selector = ".MuiBox-root.mui-style-h3npb"
    isbn_10_selector = ".MuiBox-root.mui-style-h3npb > p:has-text('ISBN-10:')"
    published_date_selector = ".MuiBox-root.mui-style-h3npb > p:has-text('Published:')"
    publisher_selector = ".MuiBox-root.mui-style-h3npb > p:has-text('Publisher:')"
    pages_selector = ".MuiBox-root.mui-style-h3npb > p:has-text('Pages:')"

    all_products = []
    try:
        # Loop through all ISBN
        for isbn in tqdm(isbn_df["ISBN13"][0:50]):
            page = context.new_page()
            page.goto(url)

            data = {
                "ISBN - 13": str(isbn),
                "Title of the Book": "",
                "Author": "",
                "Book Type": "",
                "Original Price": "",
                "Discounted Price": "",
                "ISBN - 10": "",
                "Published Date": "",
                "Publisher": "",
                "No of Pages": ""
            }

            try:
                # It will call search function and search for ISBN
                search(page, str(isbn))

                # Wait for title to load
                page.wait_for_selector(title_selector, timeout=10000)

                # Check if title is not found
                if page.locator(title_selector).count() == 0:
                    data["Title of the Book"] = "book not found"
                else:
                    data["Title of the Book"] = get_text(page, title_selector)
                    data["Author"] = clean_author_text(get_text(page, author_selector))
                    data["Book Type"] = get_text(page, book_type_selector)
                    data["Original Price"] = get_text(page, original_price_selector)
                    data["Discounted Price"] = get_text(page, discounted_price_selector)

                    # Click on details tab
                    page.click(details_tab_selector)

                    # Wait for details section
                    page.wait_for_selector(details_section_selector)

                    data["ISBN - 10"] = get_text(page, isbn_10_selector).replace("ISBN-10: ", "").strip()
                    data["Published Date"] = get_text(page, published_date_selector).replace("Published: ", "").strip()
                    data["Publisher"] = get_text(page, publisher_selector).replace("Publisher: ", "").strip()
                    data["No of Pages"] = get_text(page, pages_selector).replace("Number of Pages: ", "").strip()

                    # Formatting published date
                    date_str = data["Published Date"].replace('st', '').replace('nd', '').replace('rd', '').replace(
                        'th', '')
                    date_obj = datetime.strptime(date_str, "%d %B %Y")
                    formatted_date = date_obj.strftime("%Y-%m-%d")

                    data["Published Date"] = formatted_date

            except PlaywrightTimeoutError:
                logging.error(f"Timeout while processing ISBN: {isbn}")
                data["Title of the Book"] = "book not found"

            except Exception as e:
                logging.error(f"Error while processing ISBN: {isbn}, Error: {str(e)}")

            all_products.append(data)
            page.close()

    except Exception as e:
        logging.error(f"Error while processing: {str(e)}")

    finally:
        # Close the browser
        context.close()
        browser.close()

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(all_products)

    # Save the DataFrame to a CSV file
    df.to_csv("files/booktopia.csv", index=False)


# This function is used to search for an ISBN
def search(page, search_query):
    try:
        page.wait_for_selector("input[placeholder='Search Title, Author or ISBN']", timeout=10000)
        page.fill("input[placeholder='Search Title, Author or ISBN']", search_query)
        page.press("input[placeholder='Search Title, Author or ISBN']", "Enter")
        page.wait_for_timeout(3000)
    except PlaywrightTimeoutError:
        logging.error(f"Timeout while trying to search for ISBN: {search_query}")
    except Exception as e:
        logging.error(f"Error while trying to search for ISBN: {search_query}, Error: {str(e)}")


# This function is used to clean the author text
def clean_author_text(text):
    text = re.sub(r"By:\s*", "", text)
    text = re.sub(r"\s*\(Translator\)", "", text)
    return text


# This function is used to get text from the selector
def get_text(page, selector):
    try:
        element = page.locator(selector)
        if element.count() > 0:
            return element.text_content().strip()
        return ""
    except Exception as e:
        logging.error(f"Error getting text for selector {selector}: {str(e)}")
        return ""


# Execution starts from here
def main():
    logging.basicConfig(filename='booktopia.log', level=logging.INFO)
    url = "https://www.booktopia.com.au/"
    file_path = os.path.join(os.getcwd(), "files/input_list.csv")
    isbn_df = pd.read_csv(file_path)
    with sync_playwright() as playwright:
        run(playwright, url, isbn_df)


if __name__ == '__main__':
    main()
