# asian-foods-scraper

Scrapes detailed product information about Asian foods from the [Wismettac e-catalog](https://ecatalog.wismettacusa.com/product.php?id=36277&branch=TOR) and writes it to a CSV for analysis.

For each category you name, the scraper expands that category in the catalog's tree, visits every sub-category beneath it, and records seven fields per product: product name, brand, category, item number, pack size, minimum order quantity, and barcode.

## Install

Requires Python 3.8+ and a local install of Google Chrome. Selenium 4.6 (this version and above bundles Selenium Manager, which fetches chromedriver itself) and later downloads a matching chromedriver on its own, so there is nothing else to set up.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Pass the category names as arguments:

```bash
python foods-scrape.py rice noodle seaweed
```

A category whose name is more than one word must be quoted, so that your shell passes it through as a single argument rather than as two categories:

```bash
python foods-scrape.py "green tea" rice "instant noodle"
```

Or run it with no arguments and it will prompt you for a comma-separated list. Here the separator is the comma, so multi-word names need no quoting:

```
$ python foods-scrape.py
Enter the foods to scrape, separated by commas: green tea, rice, instant noodle
```

Either way, matching ignores capitalization and extra spaces, so `"green tea"`, `"GREEN TEA"`, and `"green  tea"` all reach the same category. The one character a name cannot contain is a double quote; the script rejects that before opening the browser.

Results go to `asian-foods.csv` in the current directory. Rows are written as each sub-category finishes, so if a later category fails you keep everything scraped up to that point.

### Options

| Flag             | Default                | Description                                                                          |
| ---------------- | ---------------------- | ------------------------------------------------------------------------------------ |
| `-o`, `--output` | `asian-foods.csv`      | Where to write the CSV                                                               |
| `-a`, `--append` | off                    | Append to an existing CSV instead of overwriting it; the header is only written once |
| `--headless`     | off                    | Run Chrome without a visible window                                                  |
| `--url`          | the catalog page above | Start from a different catalog page or branch                                        |
| `--timeout`      | `20`                   | Seconds to wait for the page to settle                                               |
| `--page-size`    | `100`                  | Products shown per catalog page                                                      |

A category name that does not exist in the catalog is reported and skipped rather than aborting the run; the exit status is non-zero if anything was skipped.

### Known limitation

The scraper reads a single catalog page per sub-category. If a sub-category holds more products than `--page-size`, the extras live on later pages and are not collected. The script prints a warning to stderr saying exactly how many it saw versus how many the catalog reported. Raising `--page-size` to whatever the catalog's dropdown offers is the workaround.

## Standalone executable

`dist/foods-scrape.exe` is a PyInstaller build for Windows. Rebuild it if you want the current behavior:

```bash
pip install pyinstaller
pyinstaller --onefile foods-scrape.py
```
