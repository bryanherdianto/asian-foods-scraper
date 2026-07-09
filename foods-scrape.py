import argparse
import csv
import sys

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

DEFAULT_URL = "https://ecatalog.wismettacusa.com/product.php?id=36277&branch=TOR"

FIELDS = [
    "Product Name",
    "Brand",
    "Category",
    "Item Number",
    "Pack Size",
    "Minimum Order Qty",
    "Barcode",
]

PRODUCT_CARD = '//div[@class="product-details"]'
RESULT_COUNT = '//*[@id="product-results"]/span'
PAGE_SIZE_SELECT = '//*[@id="productNumShow"]'

# Pulls every product card's first seven fields in a single round trip. Reading
# them one WebElement at a time costs ~8 calls per product, which dominates the
# runtime on a 100-row page. Mirrors Selenium's own text semantics: a nested
# <span> may be hidden, so read its textContent rather than the rendered text.
EXTRACT_ROWS_JS = """
return Array.from(document.querySelectorAll('div[class="product-details"]')).map(card =>
    Array.from(card.children)
        .filter(child => child.tagName === 'DIV')
        .slice(0, %d)
        .map(cell => {
            const span = cell.querySelector('span');
            return (span ? span.textContent : cell.innerText) || '';
        })
);
""" % len(FIELDS)


def normalize(food):
    """Match the XPath's normalize-space(): collapse internal runs of whitespace."""
    return " ".join(food.split()).upper()


def build_driver(headless):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    # Selenium 4.6+ downloads and manages the matching chromedriver itself.
    return webdriver.Chrome(options=options)


def wait_for_products(wait, page_size):
    """Block until the rendered card count agrees with the catalog's own count.

    The catalog re-renders asynchronously after a category click and after a
    page-size change. Comparing rendered-vs-reported is the only signal that
    holds for both, so we never read a half-swapped page.
    """

    def rendered_matches_reported(driver):
        try:
            reported = int(driver.find_element(By.XPATH, RESULT_COUNT).text)
        except (NoSuchElementException, StaleElementReferenceException, ValueError):
            return False
        if reported == 0:
            return (0, 0)
        rendered = len(driver.find_elements(By.XPATH, PRODUCT_CARD))
        if rendered and rendered == min(reported, page_size):
            return (reported, rendered)
        return False

    return wait.until(rendered_matches_reported)


def set_page_size(driver, wait, page_size):
    dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, PAGE_SIZE_SELECT)))
    select = Select(dropdown)
    value = str(page_size)
    if select.first_selected_option.get_attribute("value") != value:
        select.select_by_value(value)


def scrape_rows(driver, wait, page_size):
    reported, _ = wait_for_products(wait, page_size)
    rows = driver.execute_script(EXTRACT_ROWS_JS)
    if reported > len(rows):
        print(
            f"  ! catalog reports {reported} products but only {len(rows)} are on "
            f"this page; the remainder are on later pages and were not scraped",
            file=sys.stderr,
        )
    return [dict(zip(FIELDS, cells)) for cells in rows if len(cells) == len(FIELDS)]


def scrape_food(driver, wait, food, page_size, writer, handle):
    """Expand one category, visit each sub-category, write its products."""
    category = f'//a[normalize-space(@title)="{normalize(food)}"]'
    sublinks = f"{category}/following-sibling::ul[1]/li/a"

    link = wait.until(EC.element_to_be_clickable((By.XPATH, category)))
    driver.execute_script("arguments[0].scrollIntoView(true);", link)
    link.click()

    count = len(wait.until(EC.presence_of_all_elements_located((By.XPATH, sublinks))))
    total = 0

    for i in range(count):
        # Re-locate every iteration: the previous click replaced the DOM nodes.
        links = wait.until(EC.presence_of_all_elements_located((By.XPATH, sublinks)))
        links[i].click()

        set_page_size(driver, wait, page_size)
        rows = scrape_rows(driver, wait, page_size)

        writer.writerows(rows)
        handle.flush()  # Keep partial results on disk if a later category fails.
        total += len(rows)

    print(f"{food}: {total} products from {count} sub-categories")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "foods",
        nargs="*",
        help="category names to scrape, e.g. rice noodles seaweed "
        "(prompted for interactively if omitted)",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="catalog page to start from")
    parser.add_argument("-o", "--output", default="asian-foods.csv", help="CSV path")
    parser.add_argument(
        "-a", "--append", action="store_true", help="append instead of overwriting"
    )
    parser.add_argument(
        "--headless", action="store_true", help="run Chrome without a visible window"
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="seconds to wait")
    parser.add_argument("--page-size", type=int, default=100, help="products per page")
    return parser.parse_args(argv)


def prompt_for_foods():
    raw = input("Enter the foods to scrape, separated by commas: ")
    return [food.strip() for food in raw.split(",") if food.strip()]


def main(argv=None):
    args = parse_args(argv)

    foods = args.foods or prompt_for_foods()
    seen = set()
    foods = [f for f in foods if not (normalize(f) in seen or seen.add(normalize(f)))]
    if not foods:
        print("No foods given, nothing to do.", file=sys.stderr)
        return 1
    if any('"' in food for food in foods):
        print("Food names cannot contain a double quote.", file=sys.stderr)
        return 1

    driver = build_driver(args.headless)
    failures = []
    try:
        driver.get(args.url)
        wait = WebDriverWait(driver, args.timeout)

        mode = "a" if args.append else "w"
        with open(args.output, mode, newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if handle.tell() == 0:
                writer.writeheader()

            for food in foods:
                try:
                    scrape_food(driver, wait, food, args.page_size, writer, handle)
                except TimeoutException:
                    failures.append(food)
                    print(
                        f"{food}: not found in the catalog (or the page never "
                        f"finished loading within {args.timeout}s) — skipping",
                        file=sys.stderr,
                    )
    except WebDriverException as exc:
        print(f"Browser error: {exc.msg or exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()

    print(f"Data saved to {args.output}")
    if failures:
        print(f"Skipped: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
