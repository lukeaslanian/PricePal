import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from thefuzz import fuzz
import inquirer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.text import Text


@dataclass
class Product:
    name: str
    price: float
    store: str
    size: Optional[str] = None
    unit: Optional[str] = None
    brand: Optional[str] = None

    @property
    def display_price(self) -> str:
        """Format price for display with unit if available"""
        if self.unit:
            return f"${self.price:.2f}/{self.unit}"
        return f"${self.price:.2f}"

    @property
    def display_name(self) -> str:
        """Format name with size and brand for display"""
        parts = []
        if self.brand and self.brand not in ["PRODUCE", "MEAT", "SEAFOOD"]:
            parts.append(self.brand)
        parts.append(self.name)
        if self.size:
            parts.append(f"({self.size})")
        return " ".join(parts)


@dataclass
class PriceComparison:
    tj_total: float
    wf_total: float
    savings: float
    cheaper_store: str
    items: List[Tuple[Optional[Product], Optional[Product]]]  # TJ, WF pairs


class WFPricesFetcher:
    """Fetches Whole Foods prices from scraped CSV"""

    def __init__(self, csv_path: str):
        self.console = Console()
        self.products = []
        self._load_csv(csv_path)

    def _load_csv(self, csv_path: str):
        """Load and parse WF price data from scraped CSV"""
        try:
            with Progress() as progress:
                task = progress.add_task("[green]Loading Whole Foods prices...", total=None)

                with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            # Parse regular price and any sale prices
                            regular_price = float(row.get('regularPrice', 0))
                            sale_price = float(row.get('salePrice', 0))
                            incremental_price = float(row.get('incrementalSalePrice', 0))

                            # Use the best available price
                            price = incremental_price or sale_price or regular_price
                            if not price:
                                continue

                            # Create product object
                            product = Product(
                                name=row['name'],
                                price=price,
                                store='WF',
                                brand=row.get('brand'),
                                unit=row.get('uom')
                            )
                            self.products.append(product)
                        except (ValueError, KeyError) as e:
                            # Skip any rows with invalid data
                            continue

            self.console.print(f"[green]Loaded {len(self.products)} WF products")

        except Exception as e:
            self.console.print(f"[red]Error loading WF prices: {e}")
            sys.exit(1)

    def find_matches(self, query: str, threshold: int = 65) -> List[Product]:
        """Find products matching query using fuzzy matching"""
        matches = []
        query = query.lower()

        for product in self.products:
            # Check for exact substring match first
            if query in product.name.lower():
                ratio = 100
            else:
                # Fall back to fuzzy matching
                ratio = fuzz.ratio(query, product.name.lower())

            if ratio >= threshold:
                matches.append(product)

        return sorted(matches, key=lambda x: fuzz.ratio(query, x.name.lower()), reverse=True)


class TJPricesFetcher:
    """Fetches Trader Joe's prices from the provided CSV dump"""

    def __init__(self, csv_path: str):
        self.console = Console()
        self.products = []
        self._load_csv(csv_path)

    def _load_csv(self, csv_path: str):
        """Load and parse TJ's price data"""
        try:
            with Progress() as progress:
                task = progress.add_task("[blue]Loading Trader Joe's prices...", total=None)

                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    # Group by item_title and keep most recent price
                    temp_products = {}
                    for row in reader:
                        title = row['item_title']
                        # Skip if price is 0.01 (placeholder) or empty
                        if not row.get('retail_price') or row.get('retail_price') == '0.01':
                            continue

                        try:
                            price = float(row['retail_price'])
                        except (ValueError, KeyError):
                            continue

                        # Update if not in dict or more recent
                        if title not in temp_products or \
                                datetime.strptime(row.get('inserted_at', '2000-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S') > \
                                datetime.strptime(temp_products[title]['date'], '%Y-%m-%d %H:%M:%S'):
                            temp_products[title] = {
                                'price': price,
                                'date': row.get('inserted_at', '2000-01-01 00:00:00')
                            }

                # Convert to Product objects
                self.products = [
                    Product(name=name, price=data['price'], store='TJ')
                    for name, data in temp_products.items()
                ]

            self.console.print(f"[blue]Loaded {len(self.products)} TJ products")

        except Exception as e:
            self.console.print(f"[red]Error loading TJ prices: {e}")
            sys.exit(1)

    def find_matches(self, query: str, threshold: int = 65) -> List[Product]:
        """Find products matching query using fuzzy matching"""
        matches = []
        query = query.lower()

        for product in self.products:
            # Check for exact substring match first
            if query in product.name.lower():
                ratio = 100
            else:
                # Fall back to fuzzy matching
                ratio = fuzz.ratio(query, product.name.lower())

            if ratio >= threshold:
                matches.append(product)

        return sorted(matches, key=lambda x: fuzz.ratio(query, x.name.lower()), reverse=True)


class PriceComparer:
    def __init__(self, tj_fetcher: TJPricesFetcher, wf_fetcher: WFPricesFetcher):
        self.tj = tj_fetcher
        self.wf = wf_fetcher
        self.console = Console()

    def _select_product(self, query: str, matches: List[Product], store: str) -> Optional[Product]:
        """Interactive product selection from matches"""
        if not matches:
            return None

        if len(matches) == 1:
            return matches[0]

        # Limit to top 10 matches
        matches = matches[:10]

        choices = [
            {
                'name': f"{p.display_name} - {p.display_price}",
                'value': p
            }
            for p in matches
        ]
        choices.append({'name': 'Skip this item', 'value': None})

        questions = [
            inquirer.List(
                'product',
                message=f'Select matching {store} product for "{query}":',
                choices=choices
            )
        ]

        answers = inquirer.prompt(questions)
        return answers['product'] if answers else None

    def compare_items(self, items: List[str]) -> PriceComparison:
        """Compare prices for a list of items between stores"""
        comparisons = []
        tj_total = 0.0
        wf_total = 0.0

        for item in items:
            item = item.strip()
            if not item:
                continue

            self.console.print(f"\n[yellow]Finding matches for: {item}")

            # Find matches in both stores
            tj_matches = self.tj.find_matches(item)
            wf_matches = self.wf.find_matches(item)

            # Let user select from matches
            tj_product = self._select_product(item, tj_matches, "Trader Joe's")
            wf_product = self._select_product(item, wf_matches, "Whole Foods")

            comparisons.append((tj_product, wf_product))

            if tj_product:
                tj_total += tj_product.price
            if wf_product:
                wf_total += wf_product.price

        savings = abs(tj_total - wf_total)
        cheaper_store = "TJ" if tj_total < wf_total else "WF"

        return PriceComparison(
            tj_total=tj_total,
            wf_total=wf_total,
            savings=savings,
            cheaper_store=cheaper_store,
            items=comparisons
        )

    def display_comparison(self, result: PriceComparison):
        """Display price comparison results in a nice table"""
        table = Table(title="Price Comparison")

        table.add_column("Item", justify="left", style="cyan")
        table.add_column("Trader Joe's", justify="right", style="blue")
        table.add_column("Whole Foods", justify="right", style="green")
        table.add_column("Savings", justify="right", style="yellow")

        for tj_prod, wf_prod in result.items:
            # Format product info
            tj_info = f"{tj_prod.display_name} - {tj_prod.display_price}" if tj_prod else "Not found"
            wf_info = f"{wf_prod.display_name} - {wf_prod.display_price}" if wf_prod else "Not found"

            # Calculate savings
            if tj_prod and wf_prod:
                savings = abs(tj_prod.price - wf_prod.price)
                cheaper = "TJ" if tj_prod.price < wf_prod.price else "WF"
                savings_text = f"${savings:.2f} ({cheaper})"
            else:
                savings_text = "N/A"

            table.add_row(
                tj_prod.name if tj_prod else wf_prod.name if wf_prod else "Unknown",
                tj_info,
                wf_info,
                savings_text
            )

        table.add_section()
        table.add_row(
            "TOTAL",
            f"${result.tj_total:.2f}",
            f"${result.wf_total:.2f}",
            f"${result.savings:.2f} ({result.cheaper_store})"
        )

        self.console.print(table)

        # Print summary
        if result.cheaper_store == "TJ":
            self.console.print(f"\n[blue]Trader Joe's is cheaper by ${result.savings:.2f}")
        else:
            self.console.print(f"\n[green]Whole Foods is cheaper by ${result.savings:.2f}")


def main():
    console = Console()

    if len(sys.argv) != 3:
        console.print("[red]Usage: python price_compare.py traderjoes.csv wholefoods.csv")
        sys.exit(1)

    # Initialize price fetchers
    try:
        tj_fetcher = TJPricesFetcher(sys.argv[1])
        wf_fetcher = WFPricesFetcher(sys.argv[2])
    except Exception as e:
        console.print(f"[red]Error initializing price fetchers: {e}")
        sys.exit(1)

    # Get items from user
    console.print("\n[yellow]Enter items to compare (comma-separated):")
    items_input = input("> ")
    items = [item.strip() for item in items_input.split(",")]

    # Compare prices
    comparer = PriceComparer(tj_fetcher, wf_fetcher)
    result = comparer.compare_items(items)

    # Display results
    console.print("\n[bold]Results:")
    comparer.display_comparison(result)


if __name__ == "__main__":
    main()