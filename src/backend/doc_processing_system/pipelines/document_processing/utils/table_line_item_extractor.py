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

    def extract_tables_from_content_list(
        self, content_list_path: Path, output_csv_path: Path, document_id: str
    ) -> bool:
        """Extract tables from MinerU content_list.json and save as CSV.

        Args:
            content_list_path: Path to content_list.json
            output_csv_path: Path to save the CSV file
            document_id: Document identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load content list
            with open(content_list_path, "r", encoding="utf-8") as f:
                content_list = json.load(f)

            # Extract table elements
            table_elements = [
                item for item in content_list if item.get("type") == "table"
            ]

            if not table_elements:
                self.logger.info("No tables found in content_list.json")
                return False

            # Process each table and create line items
            all_line_items = []
            line_item_id = 1

            for table_index, table_element in enumerate(table_elements):
                try:
                    # Extract table HTML from table_body
                    html_table = table_element.get("table_body", "")

                    if not html_table:
                        self.logger.warning(f"Table {table_index} has no table_body")
                        continue

                    # Use pandas to read HTML table
                    dfs = pd.read_html(StringIO(html_table))

                    for df in dfs:
                        # Convert table to line items with JSON data
                        table_line_items = self._convert_dataframe_to_line_items(
                            df, document_id, line_item_id, table_index
                        )
                        all_line_items.extend(table_line_items)
                        line_item_id += len(table_line_items)

                        self.logger.info(
                            f"Converted table {table_index} to {len(table_line_items)} line items"
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to parse table {table_index}: {e}")

            # Save line items to CSV
            if all_line_items:
                return self.save_line_items_to_csv(all_line_items, output_csv_path)
            else:
                self.logger.warning("No line items were extracted")
                return False

        except Exception as e:
            self.logger.error(f"Failed to extract tables from content_list: {e}")
            return False

    def extract_tables_to_line_items(
        self, markdown_content: str, document_id: str
    ) -> List[Dict[str, Any]]:
        """Extract all HTML tables from markdown and convert to line items.
        DEPRECATED: Use extract_tables_from_content_list instead.

        Args:
            markdown_content: Markdown content containing HTML tables
            document_id: Document identifier

        Returns:
            List of line item dictionaries
        """
        try:
            # Extract HTML tables using regex
            table_pattern = r"<table>.*?</table>"
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

                        self.logger.info(
                            f"Converted table {table_index} to {len(table_line_items)} line items"
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to parse table {table_index}: {e}")

            return all_line_items

        except Exception as e:
            self.logger.error(f"Failed to extract tables to line items: {e}")
            return []

    def save_line_items_to_csv(
        self, line_items: List[Dict[str, Any]], output_path: Path
    ) -> bool:
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

            self.logger.info(
                f"✅ Saved {len(line_items)} line items to CSV: {output_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to save line items to CSV: {e}")
            return False

    def _convert_dataframe_to_line_items(
        self, df: pd.DataFrame, document_id: str, start_id: int, table_index: int
    ) -> List[Dict[str, Any]]:
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

        # Extract column headers from the dataframe
        # Use the first data row as column names if available
        column_names = self._extract_column_names(df)

        # Process every single row - no skipping based on content
        for row_index, row in df.iterrows():
            # Get the first column as line_item_label (could be empty)
            first_col_value = row.iloc[0] if pd.notna(row.iloc[0]) else None
            line_item_label = (
                str(first_col_value).strip()
                if first_col_value is not None
                else f"row_{row_index}"
            )

            # Convert all columns to JSON data with original column names
            data_json = {}

            for col_index in range(len(row)):
                # Get the original column name
                col_name = (
                    column_names[col_index]
                    if col_index < len(column_names)
                    else f"column_{col_index}"
                )

                # Get the cell value - preserve None for empty cells to maintain positioning
                cell_value = row.iloc[col_index]

                if pd.notna(cell_value):
                    value = str(cell_value).strip()
                    data_json[col_name] = value if value else None
                else:
                    # Preserve None for empty cells to maintain column positioning
                    data_json[col_name] = None

            # Create line item - always create to preserve table structure
            line_item = {
                "line_item_id": start_id + len(line_items),
                "line_item_label": line_item_label,
                "data_json": json.dumps(data_json, ensure_ascii=False),
                "table_source_index": table_index,
                "row_index": row_index,
            }
            line_items.append(line_item)

        return line_items

    def _extract_column_names(self, df: pd.DataFrame) -> List[str]:
        """Extract meaningful column names from DataFrame.

        Args:
            df: Pandas DataFrame

        Returns:
            List of column names
        """
        # First, try to use the pandas column names if they look meaningful
        pandas_columns = [str(col) for col in df.columns]

        # Check if pandas columns are just integers (0, 1, 2, etc.) which means no headers
        if all(col.isdigit() for col in pandas_columns):
            # Look for a header row in the data
            header_row = self._find_header_row(df)
            if header_row is not None:
                # Use the header row as column names
                header_names = []
                for col_idx in range(len(df.columns)):
                    if col_idx < len(header_row) and pd.notna(header_row.iloc[col_idx]):
                        col_name = str(header_row.iloc[col_idx]).strip()
                        header_names.append(
                            col_name if col_name else f"column_{col_idx}"
                        )
                    else:
                        header_names.append(f"column_{col_idx}")
                return header_names
            else:
                # No meaningful headers found, use generic names
                return [f"column_{i}" for i in range(len(df.columns))]
        else:
            # Use pandas column names as they seem meaningful
            return pandas_columns

    def _find_header_row(self, df: pd.DataFrame) -> pd.Series:
        """Find the row that likely contains column headers.

        Args:
            df: Pandas DataFrame

        Returns:
            Series representing the header row, or None if not found
        """
        # Look for the first row that contains text that looks like headers
        # This is a simple heuristic - can be improved
        for idx, row in df.iterrows():
            row_text = " ".join([str(val) for val in row if pd.notna(val)]).lower()
            # Check if this row contains common header words (language agnostic approach)
            if (
                len(row_text) > 5
                and not row_text.replace(" ", "")
                .replace(".", "")
                .replace(",", "")
                .isdigit()
            ):
                # This row has text content, likely a header
                return row

        # If no clear header found, return the first row
        return df.iloc[0] if len(df) > 0 else None

    def extract_and_save_tables(
        self, markdown_path: Path, processing_dir: Path, document_id: str
    ) -> bool:
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
            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Extract tables to line items
            line_items = self.extract_tables_to_line_items(
                markdown_content, document_id
            )

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
