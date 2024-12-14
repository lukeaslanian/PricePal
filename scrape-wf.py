import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import datetime


class WholeFoodsScraper:
    """
    Precision-engineered web scraper for Whole Foods 365 product listings.

    Methodical approach to product data extraction with rigorous price parsing.
    """

    BASE_URL = "https://www.wholefoodsmarket.com/products/all-products"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    @staticmethod
    def extract_price(price_text: str) -> float:
        """
        Precisely extract numeric price from text.

        Args:
            price_text (str): Raw price string

        Returns:
            float: Extracted numeric price value

        Methodology:
        1. Remove currency symbol
        2. Handle potential '/lb' or other unit indicators
        3. Convert to float with error handling
        """
        try:
            # Remove currency symbol and any trailing unit indicators
            cleaned_price = re.sub(r'/.*$', '', price_text.replace('$', '').strip())
            return float(cleaned_price)
        except (ValueError, TypeError):
            print(f"Price parsing error for input: {price_text}")
            return 0.0

    def scrape_products(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Comprehensive product scraping method with precise extraction.

        Args:
            max_pages (int): Maximum number of pages to scrape

        Returns:
            List of product dictionaries with extracted details
        """
        all_products = []

        for page in range(1, max_pages + 1):
            print(f"Systematically processing page {page}")

            try:
                # Construct request with precise parameters
                response = requests.get(
                    self.BASE_URL,
                    headers=self.HEADERS,
                    params={
                        'page': page,
                        'featured': '365-by-whole-foods-market'
                    }
                )

                # Validate network request
                response.raise_for_status()

                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Locate product tiles with precision
                product_tiles = soup.find_all('div', class_='w-pie--product-tile')

                # Terminate if no more products found
                if not product_tiles:
                    break

                # Systematic product extraction
                for tile in product_tiles:
                    # Precise content extraction
                    content_div = tile.find('div', class_='w-pie--product-tile__content')
                    if not content_div:
                        continue

                    # Brand extraction
                    brand_elem = content_div.find('span', class_='w-cms--font-disclaimer')
                    brand = brand_elem.text.strip() if brand_elem else 'Unknown Brand'

                    # Product name extraction
                    name_elem = content_div.find('h2', class_='w-cms--font-body__sans-bold')
                    name = name_elem.text.strip() if name_elem else 'Unnamed Product'

                    # Precise price extraction
                    price_elem = content_div.find('span', class_='text-left bds--heading-5')
                    price = self.extract_price(price_elem.text) if price_elem else 0.0

                    # Construct product dictionary
                    product = {
                        'sku': None,
                        'retail_price': price,
                        'item_title': f"{brand} {name}",
                        'inserted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'store_code': '365WF',
                        'availability': 1
                    }

                    # Filter out zero-priced products
                    if price > 0:
                        all_products.append(product)

                # Respectful scraping delay
                time.sleep(1)

            except requests.RequestException as e:
                print(f"Network request error on page {page}: {e}")
                break

        return all_products

    def save_to_csv(self, products: List[Dict[str, Any]], filename: str = 'whole_foods_365_products.csv') -> None:
        """
        Methodical CSV generation with precise formatting.

        Args:
            products (List[Dict]): Extracted product data
            filename (str): Output CSV filename
        """
        if not products:
            print("No products available for CSV generation.")
            return

        # Predefined CSV field specification
        fieldnames = [
            'sku', 'retail_price', 'item_title',
            'inserted_at', 'store_code', 'availability'
        ]

        # Systematic CSV writing
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write headers
            writer.writeheader()

            # Enumerate and write products with sequential SKU
            for idx, product in enumerate(products, 1):
                product_row = product.copy()
                product_row['sku'] = f'WF365-{idx:05d}'
                writer.writerow(product_row)

        print(f"Successfully generated CSV with {len(products)} products")


def main():
    """
    Primary execution orchestrator for Whole Foods 365 product scraping.
    """
    scraper = WholeFoodsScraper()

    # Initiate comprehensive product extraction
    products = scraper.scrape_products(max_pages=5)

    # Generate output CSV
    scraper.save_to_csv(products)

    # Diagnostic output
    print(f"Total unique products extracted: {len(products)}")
    print("\nPrice Distribution Snapshot:")
    price_ranges = {
        '< $5': len([p for p in products if p['retail_price'] < 5]),
        '$5 - $10': len([p for p in products if 5 <= p['retail_price'] < 10]),
        '$10 - $20': len([p for p in products if 10 <= p['retail_price'] < 20]),
        '> $20': len([p for p in products if p['retail_price'] >= 20])
    }
    for range_desc, count in price_ranges.items():
        print(f"{range_desc}: {count} products")


if __name__ == "__main__":
    main()