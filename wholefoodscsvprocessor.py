import csv
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any


class WholeFootsCSVProcessor:
    def __init__(self, input_path: str, output_path: str):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            filename='whole_foods_processing.log',
            filemode='w'
        )

        self.input_path = input_path
        self.output_path = output_path

        self.stats = {
            'total_rows': 0,
            'processed_rows': 0,
            'skipped_rows': 0,
            'skip_reasons': {}
        }

    def process_csv(self) -> None:
        """
        Minimally filtered CSV processing method
        """
        logging.info(f"Starting CSV processing: {self.input_path}")

        processed_names = set()

        try:
            with open(self.input_path, 'r', encoding='utf-8') as infile, \
                    open(self.output_path, 'w', newline='', encoding='utf-8') as outfile:

                reader = csv.DictReader(infile)

                # Output CSV headers
                fieldnames = [
                    'sku', 'retail_price', 'item_title',
                    'inserted_at', 'store_code', 'availability'
                ]
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sku_counter = 0

                for row in reader:
                    self.stats['total_rows'] += 1

                    # Basic name validation
                    name = str(row.get('name', '')).strip()
                    if not name or len(name) < 2:
                        continue

                    # Prevent exact duplicate names
                    if name in processed_names:
                        continue
                    processed_names.add(name)

                    # Assign a price if no price is available
                    sku_counter += 1
                    writer.writerow({
                        'sku': f'WF{sku_counter:05d}',
                        'retail_price': '0.01',  # Minimal default price
                        'item_title': name,
                        'inserted_at': timestamp,
                        'store_code': '546',
                        'availability': '1'
                    })
                    self.stats['processed_rows'] += 1

        except Exception as e:
            logging.error(f"Critical processing error: {e}")
            raise

        finally:
            self._log_processing_summary()

    def _log_processing_summary(self):
        """
        Generate comprehensive processing summary log
        """
        logging.info("\n🔍 Processing Summary 🔍")
        logging.info(f"Total Rows Processed: {self.stats['total_rows']}")
        logging.info(f"Valid Products: {self.stats['processed_rows']}")

        processing_rate = (self.stats['processed_rows'] / self.stats['total_rows'] * 100) if self.stats[
                                                                                                 'total_rows'] > 0 else 0
        logging.info(f"Processing Rate: {processing_rate:.2f}%")


def main():
    if len(sys.argv) != 3:
        print("Usage: python whole_foods_csv_processor.py input.csv output.csv")
        sys.exit(1)

    processor = WholeFootsCSVProcessor(sys.argv[1], sys.argv[2])
    processor.process_csv()
    print("CSV processing completed. Check logs for details.")


if __name__ == '__main__':
    main()