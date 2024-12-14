# Whole Foods vs. Trader Joes Grocery Price Comparison Tool

## Overview
A TUI Python-based price comparison utility designed to analyze and compare product prices across different grocery stores, with a focus on Trader Joe's and Whole Foods Market datasets.

## Features
- Robust price extraction from CSV sources
- Intelligent product matching
- Detailed price comparison reporting
- Flexible input handling for multiple grocery store formats

## Prerequisites
- Python 3.7+
- Required Libraries:
  - `rich` (for enhanced console output)
  - `thefuzz` (for product name matching)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/grocery-price-comparison.git
cd grocery-price-comparison
```

2. Install required dependencies:
```bash
pip install rich thefuzz
```

## Usage

### Basic Price Comparison
```bash
python price-comp.py [trader_joes_csv] [whole_foods_csv]
```

#### Example
```bash
python price-comp.py dump.csv whole_foods_products.csv
```

### Sample Output
```
Enter item to compare (or 'done' to finish): carrots

Trader Joe's Matches:
             Trader Joe's matches for 'carrots'             
╭────┬────────────────────────────────────┬───────┬────────╮
│ #  │ Product                            │ Price │ SKU    │
├────┼────────────────────────────────────┼───────┼────────┤
│ 1  │ Cut and Peeled Carrots             │ $1.99 │ 070588 │
│ 2  │ Organic Carrots of Many Colors     │ $2.99 │ 051475 │
...
╰────┴────────────────────────────────────┴───────┴────────╯
Select Trader Joe's product (1-10, or 's' to skip): 2

Whole Foods Matches:
                  Whole Foods matches for 'carrots'                  
╭───┬─────────────────────────────────────────────┬───────┬─────────╮
│ # │ Product                                     │ Price │ SKU     │
├───┼─────────────────────────────────────────────┼───────┼─────────┤
│ 1 │ Organic Carrots (5 Pound)                   │ $4.99 │ WF00016 │
│ 2 │ Organic Petite Baby Carrots                 │ $2.79 │ WF00903 │
│ 3 │ Organic Peeled Baby Rainbow Carrots         │ $2.49 │ WF00668 │
...
╰───┴─────────────────────────────────────────────┴───────┴─────────╯
Select Whole Foods product (1-5, or 's' to skip): 3

Final Comparison Results:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━┓
┃ Item                         │ Trader Joe's  │ Whole Foods   │ Savings ┃
┠────────────────────────────────────────────────────────────────────────┨
┃ Organic Carrots              │ $2.99         │ $2.49         │ $0.50   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━┛
```

### Detailed Usage Notes
- Enter product names to compare
- Select specific items from matched results
- Use 's' to skip if no matching item found
- Type 'done' to finish comparison

### Input File Requirements
- **Trader Joe's CSV**: Structured CSV with product details
- **Whole Foods CSV**: Processed CSV from included sanitization script

## Data Preparation

### Whole Foods Data Sanitization
1. Place raw Whole Foods product list in `wf-input.txt`
2. Run sanitization script:
```bash
python sanitize.py
```
3. Generated file: `whole_foods_products.csv`

## Workflow
1. Prepare input CSVs
2. Run price comparison script
3. Review detailed price comparison output in console

## Advanced Features
- Fuzzy product name matching
- Detailed price variance reporting
- Store-specific price analysis

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License

## Disclaimer
Prices and product availability may vary. Always verify current pricing at the store.

## Support
For issues or feature requests, please file a GitHub issue.
```