import csv
import sys
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import thefuzz.fuzz as fuzz
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box


@dataclass
class Product:
    name: str
    price: float
    store: str
    size: Optional[str] = None
    unit: Optional[str] = None
    brand: Optional[str] = None
    sku: Optional[str] = None

    @property
    def display_price(self) -> str:
        """Format price with optional unit."""
        if self.unit:
            return f"${self.price:.2f}/{self.unit}"
        return f"${self.price:.2f}"

    @property
    def display_name(self) -> str:
        """Create a comprehensive product display name."""
        parts = []
        if self.brand and self.brand not in ["PRODUCE", "MEAT", "SEAFOOD"]:
            parts.append(self.brand)
        parts.append(self.name)
        if self.size:
            parts.append(f"({self.size})")
        return " ".join(parts)


@dataclass
class PriceComparison:
    """Detailed price comparison results."""
    tj_total: float
    wf_total: float
    savings: float
    cheaper_store: str
    items: List[Tuple[Optional[Product], Optional[Product]]]


class StoreDataLoader:
    """Enhanced data loader with robust parsing."""

    def __init__(self, console: Console):
        self.console = console

    async def load_data(self, csv_path: str, store_name: str, color: str) -> List[Product]:
        """
        Asynchronously load product data from CSV with progress tracking.

        Args:
            csv_path (str): Path to the CSV file
            store_name (str): Name of the store for display
            color (str): Console color for progress display

        Returns:
            List[Product]: Parsed list of products
        """
        products = []
        with Progress(
                SpinnerColumn(),
                TextColumn(f"[{color}]Loading {store_name} data..."),
                transient=True,
                console=self.console
        ) as progress:
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    # Skip potential duplicate header rows
                    reader = csv.DictReader(
                        (row for row in f if not row.startswith('sku,') and row.strip()),
                        fieldnames=['sku', 'retail_price', 'item_title', 'inserted_at', 'store_code', 'availability']
                    )

                    for row in reader:
                        product = self._parse_row(row, store_name)
                        if product:
                            products.append(product)

                self.console.print(f"[{color}]✓ Loaded {len(products)} products from {store_name}")
                return products
            except Exception as e:
                self.console.print(f"[red]Error loading {store_name} data: {e}")
                return []

    @staticmethod
    def _remove_duplicates(products: List[Product]) -> List[Product]:
        """
        Remove duplicate products while preserving first occurrence.

        Args:
            products (List[Product]): List of input products

        Returns:
            List[Product]: Deduplicated list of products
        """
        # Create a unique key for each product
        unique_products = {}
        for product in products:
            # Use name and price as unique identifier
            unique_key = (product.name, product.price)
            if unique_key not in unique_products:
                unique_products[unique_key] = product

        return list(unique_products.values())

    async def load_data(self, csv_path: str, store_name: str, color: str) -> List[Product]:
        """
        Enhanced data loading with duplicate removal and intelligent filtering.

        Args:
            csv_path (str): Path to the CSV file
            store_name (str): Name of the store
            color (str): Console color for progress display

        Returns:
            List[Product]: Parsed and deduplicated list of products
        """
        products = []
        with Progress(
                SpinnerColumn(),
                TextColumn(f"[{color}]Loading {store_name} data..."),
                transient=True,
                console=self.console
        ) as progress:
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    # Skip duplicate header rows
                    reader = csv.DictReader(
                        (row for row in f if not row.startswith('sku,') and row.strip()),
                        fieldnames=['sku', 'retail_price', 'item_title', 'inserted_at', 'store_code', 'availability']
                    )

                    for row in reader:
                        product = self._parse_row(row, store_name)
                        if product:
                            products.append(product)

                # Remove duplicates
                deduplicated_products = self._remove_duplicates(products)

                self.console.print(f"[{color}]✓ Loaded {len(deduplicated_products)} unique products from {store_name}")
                return deduplicated_products
            except Exception as e:
                self.console.print(f"[red]Error loading {store_name} data: {e}")
                return []

    def _parse_row(self, row: Dict, store: str) -> Optional[Product]:
        """
        Sophisticated parsing with nuanced price and product filtering.

        Args:
            row (Dict): Dictionary of row data
            store (str): Store name

        Returns:
            Optional[Product]: Parsed product or None if invalid
        """
        try:
            # Handle price parsing with advanced filtering
            price_str = row.get('retail_price', '0')
            price = float(price_str)

            # Intelligent filtering strategy
            if store == 'WF':
                # Whole Foods specific parsing
                # Keep $0.01 prices for meaningful products
                if price == 0.01:
                    meaningful_keywords = [
                        'olive', 'oil', 'organic', 'tuna', 'virgin',
                        'extra virgin', 'white', 'potato', 'chips',
                        'anchovy', 'couscous', 'rice', 'garlic'
                    ]
                    item_title = row.get('item_title', '').lower()

                    # More lenient matching for Whole Foods placeholder prices
                    if not any(keyword in item_title for keyword in meaningful_keywords):
                        return None

            # Trader Joe's specific filtering
            elif store == 'TJ':
                # Stricter filtering for Trader Joe's
                if price <= 0.01:
                    return None

            return Product(
                name=row.get('item_title', '').strip(),
                price=price,
                store=store,
                sku=row.get('sku')
            )
        except (ValueError, TypeError):
            return None


class EnhancedPriceComparer:
    """Advanced price comparison tool with fuzzy matching and rich display."""

    def __init__(self, tj_products: List[Product], wf_products: List[Product]):
        self.tj_products = tj_products
        self.wf_products = wf_products
        self.console = Console()
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        """Configure rich console layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

    def _find_matches(self, query: str, products: List[Product], threshold: int = 65) -> List[Product]:
        """
        Find product matches using fuzzy string matching.

        Args:
            query (str): Search query
            products (List[Product]): List of products to search
            threshold (int): Minimum match score

        Returns:
            List[Product]: Sorted list of matched products
        """
        matches = []
        query = query.lower()

        for product in products:
            # Exact match or fuzzy score check
            if query in product.name.lower():
                ratio = 100
            else:
                ratio = fuzz.ratio(query, product.name.lower())

            if ratio >= threshold:
                matches.append(product)

        return sorted(matches, key=lambda x: fuzz.ratio(query, x.name.lower()), reverse=True)[:10]

    def compare_items(self) -> PriceComparison:
        """
        Interactive price comparison process.

        Returns:
            PriceComparison: Detailed comparison results
        """
        comparisons = []
        tj_total = 0.0
        wf_total = 0.0

        while True:
            self.console.clear()
            item = Prompt.ask("\nEnter item to compare (or 'done' to finish)")
            if item.lower() == 'done':
                break

            # Find and display matches
            tj_matches = self._find_matches(item, self.tj_products)
            wf_matches = self._find_matches(item, self.wf_products)

            self.console.print("\n[bold blue]Trader Joe's Matches:")
            tj_product = self._display_matches(tj_matches, "Trader Joe's", item)

            self.console.print("\n[bold green]Whole Foods Matches:")
            wf_product = self._display_matches(wf_matches, "Whole Foods", item)

            comparisons.append((tj_product, wf_product))

            # Update totals
            if tj_product:
                tj_total += tj_product.price
            if wf_product:
                wf_total += wf_product.price

            continue_shopping = Confirm.ask("\nAdd another item?", default=True)
            if not continue_shopping:
                break

        # Calculate savings and cheaper store
        savings = abs(tj_total - wf_total)
        cheaper_store = "TJ" if tj_total < wf_total else "WF"

        return PriceComparison(
            tj_total=tj_total,
            wf_total=wf_total,
            savings=savings,
            cheaper_store=cheaper_store,
            items=comparisons
        )

    def _display_matches(self, matches: List[Product], store: str, query: str) -> Optional[Product]:
        """
        Display product matches and allow user selection.

        Args:
            matches (List[Product]): List of matched products
            store (str): Store name
            query (str): Original search query

        Returns:
            Optional[Product]: Selected product or None
        """
        if not matches:
            self.console.print(f"[yellow]No matches found for '{query}' in {store}")
            return None

        table = Table(
            box=box.ROUNDED,
            title=f"[bold]{store} matches for '{query}'",
            show_header=True,
            header_style="bold"
        )

        table.add_column("#", style="dim")
        table.add_column("Product", style="cyan")
        table.add_column("Price", justify="right", style="green")
        table.add_column("SKU", style="dim")

        for idx, product in enumerate(matches, 1):
            table.add_row(
                str(idx),
                product.display_name,
                product.display_price,
                product.sku or "N/A"
            )

        self.console.print(table)

        # Prompt for selection
        choice = Prompt.ask(
            f"Select {store} product (1-{len(matches)}, or 's' to skip)",
            choices=[str(i) for i in range(1, len(matches) + 1)] + ['s'],
            default='s'
        )

        return matches[int(choice) - 1] if choice != 's' else None

    def display_comparison(self, result: PriceComparison):
        """
        Display comprehensive price comparison results.

        Args:
            result (PriceComparison): Comparison results to display
        """
        table = Table(
            title="Price Comparison Results",
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("Item", style="cyan")
        table.add_column("Trader Joe's", justify="right", style="blue")
        table.add_column("Whole Foods", justify="right", style="green")
        table.add_column("Savings", justify="right", style="yellow")

        for tj_prod, wf_prod in result.items:
            # Detailed product information display
            tj_info = f"{tj_prod.display_name} - {tj_prod.display_price}" if tj_prod else "Not found"
            wf_info = f"{wf_prod.display_name} - {wf_prod.display_price}" if wf_prod else "Not found"

            # Calculate savings
            if tj_prod and wf_prod:
                savings = abs(tj_prod.price - wf_prod.price)
                cheaper = "TJ" if tj_prod.price < wf_prod.price else "WF"
                savings_text = f"${savings:.2f} ({cheaper})"
            else:
                savings_text = "N/A"

            # Add row to results table
            table.add_row(
                tj_prod.name if tj_prod else wf_prod.name if wf_prod else "Unknown",
                tj_info,
                wf_info,
                savings_text
            )

        # Total summary
        table.add_section()
        table.add_row(
            "TOTAL",
            f"${result.tj_total:.2f}",
            f"${result.wf_total:.2f}",
            f"${result.savings:.2f} ({result.cheaper_store})",
            style="bold"
        )

        # Display final results
        self.console.clear()
        self.layout["main"].update(table)

        # Highlight cheaper store
        summary_style = "bold blue" if result.cheaper_store == "TJ" else "bold green"
        store_name = "Trader Joe's" if result.cheaper_store == "TJ" else "Whole Foods"
        summary = f"{store_name} is cheaper by ${result.savings:.2f}"

        # Update layout and display
        self.layout["footer"].update(
            Panel(
                Text(summary, style=summary_style, justify="center"),
                style="dim"
            )
        )
        self.console.print(self.layout)


async def main():
    """
    Main application entry point with error handling.

    Loads store data and initiates price comparison process.
    """
    console = Console()

    # Validate command-line arguments
    if len(sys.argv) != 3:
        console.print("[red]Usage: python price_compare.py traderjoes.csv whole_foods_products.csv")
        sys.exit(1)

    # Initialize data loader
    loader = StoreDataLoader(console)

    # Load store data
    tj_products = await loader.load_data(sys.argv[1], "Trader Joe's", "blue")
    wf_products = await loader.load_data(sys.argv[2], "Whole Foods", "green")

    # Validate data loading
    if not tj_products or not wf_products:
        console.print("[red]Failed to load product data. Exiting.")
        sys.exit(1)

    # Initialize and run price comparer
    comparer = EnhancedPriceComparer(tj_products, wf_products)
    result = comparer.compare_items()

    # Display final comparison
    comparer.display_comparison(result)


if __name__ == "__main__":
    asyncio.run(main())