"""
TableLineItemExtractor - Generic table extraction to line items with JSON data.
Extracts all table data without string-based filtering or assumptions.
"""

import logging
import json
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from io import StringIO


class TableLineItemExtractor:
    """Generic table extractor that converts all table data to line items with JSON."""

    def __init__(self, logger: logging.Logger = None):
        """Initialize the table extractor.

        Args:
            logger: Logger instance to use for logging
        """
        self.logger = logger or logging.getLogger(__name__)

    def extract_tables_to_line_items(self, markdown_content: str, document_id: str) -> List[Dict[str, Any]]:
        """Extract all HTML tables from markdown and convert to line items.

        Args:
            markdown_content: Markdown content containing HTML tables
            document_id: Document identifier

        Returns:
            List of line item dictionaries
        """
        try:
            # Extract HTML tables using regex
            table_pattern = r'<table>.*?</table>'
            html_tables = re.findall(table_pattern, markdown_content, re.DOTALL)

            if not html_tables:
                self.logger.info("No HTML tables found in markdown")
                return []

            # Process each table and create line items
            all_line_items = []
            line_item_id = 1

            for table_index, html_table in enumerate(html_tables):
                try:
                    # Use pandas to read HTML table
                    dfs = pd.read_html(StringIO(html_table))

                    for df in dfs:
                        # Convert table to line items with JSON data
                        table_line_items = self._convert_dataframe_to_line_items(
                            df, document_id, line_item_id, table_index
                        )
                        all_line_items.extend(table_line_items)
                        line_item_id += len(table_line_items)

                        self.logger.info(f"Converted table {table_index} to {len(table_line_items)} line items")

                except Exception as e:
                    self.logger.warning(f"Failed to parse table {table_index}: {e}")

            return all_line_items

        except Exception as e:
            self.logger.error(f"Failed to extract tables to line items: {e}")
            return []

    def save_line_items_to_csv(self, line_items: List[Dict[str, Any]], output_path: Path) -> bool:
        """Save line items to CSV file.

        Args:
            line_items: List of line item dictionaries
            output_path: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not line_items:
                self.logger.warning("No line items to save")
                return False

            # Create DataFrame with line items
            line_items_df = pd.DataFrame(line_items)

            # Save as CSV
            line_items_df.to_csv(output_path, index=False)

            self.logger.info(f"✅ Saved {len(line_items)} line items to CSV: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save line items to CSV: {e}")
            return False

    def _convert_dataframe_to_line_items(self, df: pd.DataFrame, document_id: str, start_id: int, table_index: int) -> List[Dict[str, Any]]:
        """Convert a pandas DataFrame to line items with JSON data format.

        Args:
            df: Pandas DataFrame from HTML table
            document_id: Document identifier
            start_id: Starting line item ID
            table_index: Index of the source table

        Returns:
            List of line item dictionaries
        """
        line_items = []

        # Get the DataFrame as-is without any filtering
        num_columns = len(df.columns)

        # Process every single row - no skipping based on content
        for row_index, row in df.iterrows():
            # Get the first column as line_item_label (could be empty)
            line_item_label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else f"row_{row_index}"

            # Convert all other columns to JSON data
            data_json = {}

            for col_index in range(num_columns):
                if pd.notna(row.iloc[col_index]):
                    value = str(row.iloc[col_index]).strip()
                    if value:  # Only add non-empty values
                        # Use generic column naming
                        json_key = f"col_{col_index}"
                        data_json[json_key] = value

            # Create line item even if data_json is minimal
            # This ensures we capture ALL table data without filtering
            line_item = {
                'line_item_id': start_id + len(line_items),
                'line_item_label': line_item_label,
                'data_json': json.dumps(data_json, ensure_ascii=False),
                'table_source_index': table_index,
                'row_index': row_index
            }
            line_items.append(line_item)

        return line_items

    def extract_and_save_tables(self, markdown_path: Path, processing_dir: Path, document_id: str) -> bool:
        """Complete pipeline: extract tables from markdown and save as line items CSV.

        Args:
            markdown_path: Path to markdown file
            processing_dir: Directory to save output
            document_id: Document identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the markdown file
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Extract tables to line items
            line_items = self.extract_tables_to_line_items(markdown_content, document_id)

            if line_items:
                # Save to CSV
                csv_path = processing_dir / f"{document_id}_line_items.csv"
                return self.save_line_items_to_csv(line_items, csv_path)
            else:
                self.logger.warning("No line items were extracted")
                return False

        except Exception as e:
            self.logger.error(f"Failed to extract and save tables: {e}")
            return False