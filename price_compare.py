import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from thefuzz import fuzz
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.style import Style
from rich import box


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
        if self.unit:
            return f"${self.price:.2f}/{self.unit}"
        return f"${self.price:.2f}"

    @property
    def display_name(self) -> str:
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
    items: List[Tuple[Optional[Product], Optional[Product]]]


class StoreDataLoader:
    def __init__(self, console: Console):
        self.console = console

    async def load_data(self, csv_path: str, store_name: str, color: str) -> List[Product]:
        products = []
        with Progress(
                SpinnerColumn(),
                TextColumn(f"[{color}]Loading {store_name} data..."),
                transient=True,
                console=self.console
        ) as progress:
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        product = self._parse_row(row, store_name)
                        if product:
                            products.append(product)

                self.console.print(f"[{color}]✓ Loaded {len(products)} products from {store_name}")
                return products
            except Exception as e:
                self.console.print(f"[red]Error loading {store_name} data: {e}")
                sys.exit(1)

    def _parse_row(self, row: Dict, store: str) -> Optional[Product]:
        try:
            if store == "WF":
                return self._parse_wf_row(row)
            else:
                return self._parse_tj_row(row)
        except (ValueError, KeyError):
            return None

    def _parse_wf_row(self, row: Dict) -> Optional[Product]:
        regular_price = float(row.get('regularPrice', 0))
        sale_price = float(row.get('salePrice', 0))
        incremental_price = float(row.get('incrementalSalePrice', 0))
        price = incremental_price or sale_price or regular_price

        if not price:
            return None

        return Product(
            name=row['name'],
            price=price,
            store='WF',
            brand=row.get('brand'),
            unit=row.get('uom')
        )

    def _parse_tj_row(self, row: Dict) -> Optional[Product]:
        if not row.get('retail_price') or row.get('retail_price') == '0.01':
            return None

        try:
            price = float(row['retail_price'])
            return Product(
                name=row['item_title'],
                price=price,
                store='TJ'
            )
        except (ValueError, KeyError):
            return None


class EnhancedPriceComparer:
    def __init__(self, tj_products: List[Product], wf_products: List[Product]):
        self.tj_products = tj_products
        self.wf_products = wf_products
        self.console = Console()
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

    def _create_header(self, title: str) -> Panel:
        return Panel(
            Text(title, style="bold white", justify="center"),
            style="blue",
            box=box.DOUBLE
        )

    def _create_footer(self, text: str) -> Panel:
        return Panel(text, style="dim")

    def _find_matches(self, query: str, products: List[Product], threshold: int = 65) -> List[Product]:
        matches = []
        query = query.lower()

        for product in products:
            if query in product.name.lower():
                ratio = 100
            else:
                ratio = fuzz.ratio(query, product.name.lower())

            if ratio >= threshold:
                matches.append(product)

        return sorted(matches, key=lambda x: fuzz.ratio(query, x.name.lower()), reverse=True)[:10]

    def _display_matches(self, matches: List[Product], store: str, query: str) -> Optional[Product]:
        if not matches:
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

        for idx, product in enumerate(matches, 1):
            table.add_row(
                str(idx),
                product.display_name,
                product.display_price
            )

        self.console.print(table)

        choice = Prompt.ask(
            f"Select {store} product (1-{len(matches)}, or 's' to skip)",
            choices=[str(i) for i in range(1, len(matches) + 1)] + ['s'],
            default='s'
        )

        return matches[int(choice) - 1] if choice != 's' else None

    def compare_items(self) -> PriceComparison:
        comparisons = []
        tj_total = 0.0
        wf_total = 0.0

        while True:
            self.console.clear()
            self.layout["header"].update(self._create_header("🛒 Price Comparison Tool"))

            item = Prompt.ask("\nEnter item to compare (or 'done' to finish)")
            if item.lower() == 'done':
                break

            tj_matches = self._find_matches(item, self.tj_products)
            wf_matches = self._find_matches(item, self.wf_products)

            self.console.print("\n[bold blue]Trader Joe's Matches:")
            tj_product = self._display_matches(tj_matches, "Trader Joe's", item)

            self.console.print("\n[bold green]Whole Foods Matches:")
            wf_product = self._display_matches(wf_matches, "Whole Foods", item)

            comparisons.append((tj_product, wf_product))

            if tj_product:
                tj_total += tj_product.price
            if wf_product:
                wf_total += wf_product.price

            continue_shopping = Confirm.ask("\nAdd another item?", default=True)
            if not continue_shopping:
                break

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
            tj_info = f"{tj_prod.display_name} - {tj_prod.display_price}" if tj_prod else "Not found"
            wf_info = f"{wf_prod.display_name} - {wf_prod.display_price}" if wf_prod else "Not found"

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
            f"${result.savings:.2f} ({result.cheaper_store})",
            style="bold"
        )

        self.console.clear()
        self.layout["header"].update(self._create_header("🛒 Final Results"))
        self.layout["main"].update(table)

        summary_style = "bold blue" if result.cheaper_store == "TJ" else "bold green"
        store_name = "Trader Joe's" if result.cheaper_store == "TJ" else "Whole Foods"
        summary = f"{store_name} is cheaper by ${result.savings:.2f}"

        self.layout["footer"].update(self._create_footer(Text(summary, style=summary_style, justify="center")))
        self.console.print(self.layout)


async def main():
    console = Console()

    if len(sys.argv) != 3:
        console.print("[red]Usage: python price_compare.py traderjoes.csv whole_foods_products.csv")
        sys.exit(1)

    loader = StoreDataLoader(console)

    # Load store data
    tj_products = await loader.load_data(sys.argv[1], "Trader Joe's", "blue")
    wf_products = await loader.load_data(sys.argv[2], "Whole Foods", "green")

    # Initialize comparer
    comparer = EnhancedPriceComparer(tj_products, wf_products)

    # Start comparison process
    result = comparer.compare_items()

    # Display results
    comparer.display_comparison(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())