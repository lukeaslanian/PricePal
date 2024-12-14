import csv
import re
from datetime import datetime


def clean_csv_field(field):
    """
    Clean and sanitize CSV field to prevent formatting issues.

    Args:
        field (str): Input field to be cleaned

    Returns:
        str: Cleaned field, properly escaped for CSV
    """
    # Handle None or empty values
    if not field:
        return ""

    # Convert to string and strip whitespace
    field = str(field).strip()

    # Escape double quotes by doubling them
    field = field.replace('"', '""')

    # If field contains comma, newline, or quote, wrap in quotes
    if ',' in field or '\n' in field or '"' in field:
        field = f'"{field}"'

    return field


def is_valid_price(price_str):
    """
    Validate if the given string represents a valid price.

    Args:
        price_str (str): String to check for price validity

    Returns:
        bool: True if string represents a valid price, False otherwise
    """
    # Remove any whitespace and currency symbols
    cleaned_price = price_str.replace('$', '').replace(',', '').replace('with Prime', '').strip()

    # Check if the cleaned string is a valid number
    try:
        # Convert to float, must be positive
        price_float = float(cleaned_price)
        return price_float > 0 and price_float < 1000  # Reasonable price range
    except ValueError:
        return False


def extract_price(price_line):
    """
    Extract a valid price from the given line.

    Args:
        price_line (str): Line containing potential price

    Returns:
        str: Extracted price, or empty string if no valid price found
    """
    # Remove noise
    price_line = price_line.replace('Add to list', '').replace('with Prime', '').strip()

    # Try to find price patterns
    price_matches = re.findall(r'\$?(\d+(?:\.\d{1,2})?)', price_line)

    # Filter and validate prices
    for match in price_matches:
        if is_valid_price(match):
            return match

    return ''


def generate_whole_foods_csv(input_file, output_file):
    """
    Convert Whole Foods product text file to structured CSV.

    Args:
        input_file (str): Path to input text file
        output_file (str): Path to output CSV file
    """
    # Consistent timestamp for all entries
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Store code for Whole Foods
    store_code = "546"

    # Default availability
    availability = "1"

    products = []

    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content into lines
    lines = content.split('\n')

    # Counter for generating SKU
    sku_counter = 1

    # Process all lines
    for i in range(0, len(lines), 2):
        # Ensure we have enough lines to process
        if i + 1 >= len(lines):
            break

        # Extract product name and price line
        product_name = lines[i].strip()
        price_line = lines[i + 1].strip()

        # Skip lines that don't look like products
        if not product_name or not price_line:
            continue

        # Skip irrelevant lines
        if (product_name in ['Add to list', '365 by Whole Foods Market', 'Opens in a new tab'] or
                price_line in ['Add to list', '365 by Whole Foods Market', 'Opens in a new tab']):
            continue

        # Skip entries with '365' in the name
        if '365' in product_name:
            continue

        # Extract price
        price = extract_price(price_line)

        # Only add if we have a valid price and a meaningful product name
        if price and len(product_name) > 3 and not re.search(r'^\d+$', product_name):
            # Generate SKU
            sku = f"WF{sku_counter:05d}"
            sku_counter += 1

            # Append to products list
            products.append([
                sku,
                price,
                clean_csv_field(product_name),
                timestamp,
                store_code,
                availability
            ])

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        csv_writer = csv.writer(f)

        # Write header
        csv_writer.writerow([
            "sku",
            "retail_price",
            "item_title",
            "inserted_at",
            "store_code",
            "availability"
        ])

        # Write products
        csv_writer.writerows(products)

    print(f"Converted {len(products)} products to CSV.")


# Example usage
if __name__ == "__main__":
    generate_whole_foods_csv("wf-input.txt", "whole_foods_products.csv")