"""
DocumentProcessor - Smart document extraction with MinerU backend.
Extracts rich markdown and tables from documents using MinerU processing.
"""

import logging
import json
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from io import StringIO
from .mu import parse_single_file
MINERU_AVAILABLE = True

class DocumentProcessor:
    """Smart document processor with format detection and adaptive pipelines."""

    def __init__(self, temp_base_dir: str = "data/temp/mineru"):
        """Initialize DocumentProcessor with MinerU backend.

        Args:
            temp_base_dir: Base directory for temporary processing files
        """
        self.logger = logging.getLogger(__name__)
        self.temp_base_dir = Path(temp_base_dir)
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)

        if not MINERU_AVAILABLE:
            self.logger.error("MinerU not available - install MinerU dependencies")
            raise ImportError("MinerU package is required but not installed")

        self.logger.info("DocumentProcessor initialized with MinerU backend")

    def extract_document(self, raw_file_path: str, document_id: str) -> Dict[str, Any]:
        """Extract document to markdown with path-based output.

        Args:
            raw_file_path: Path to raw document file
            document_id: Unique document identifier

        Returns:
            Dict with paths to extracted content: {
                "status": "completed",
                "processed_markdown_path": "/path/to/document.md",
                "document_id": "doc_id",
                "file_info": {...}
            }
        """
        try:
            raw_path = Path(raw_file_path)
            if not raw_path.exists():
                return self._error_result("File not found", raw_file_path)

            self.logger.info(f"Starting MinerU extraction for: {raw_path.name}")

            # Step 1: Create processing directory
            processing_dir = self._create_processing_directory(document_id)

            # Step 2: Use MinerU to process document
            parse_single_file(
                file_path=raw_path,
                output_dir=str(processing_dir),
                backend="pipeline"
            )

            # Step 3: Find the generated markdown file
            expected_output_dir = processing_dir / f"{raw_path.stem}_output"
            markdown_path = expected_output_dir / f"{raw_path.stem}.md"

            if not markdown_path.exists():
                return self._error_result("MinerU markdown not generated", raw_file_path)

            # Step 4: Copy markdown to expected location
            final_markdown_path = processing_dir / f"{document_id}_mineru.md"
            with open(markdown_path, 'r', encoding='utf-8') as src:
                with open(final_markdown_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            # Step 5: Extract tables from markdown and save as CSV
            self._extract_tables_to_csv(final_markdown_path, processing_dir, document_id)

            # Step 6: Get file metadata
            file_info = self._get_file_info(raw_path)

            self.logger.info(f"✅ MinerU extraction completed: {final_markdown_path}")

            return {
                "status": "completed",
                "processed_markdown_path": str(final_markdown_path),
                "document_id": document_id,
                "file_info": file_info,
                "processing_directory": str(processing_dir)
            }

        except Exception as e:
            self.logger.error(f"❌ MinerU extraction failed: {e}")
            return self._error_result("Extraction failed", raw_file_path, error_details=str(e))

    # HELPER FUNCTIONS
    def _extract_tables_to_csv(self, markdown_path: Path, processing_dir: Path, document_id: str):
        """Extract HTML tables from markdown and save as combined CSV."""
        try:
            # Read the markdown file
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Extract HTML tables using regex
            table_pattern = r'<table>.*?</table>'
            html_tables = re.findall(table_pattern, markdown_content, re.DOTALL)

            if not html_tables:
                self.logger.info("No HTML tables found in markdown")
                return

            # Parse each table with pandas
            all_dataframes = []
            for i, html_table in enumerate(html_tables):
                try:
                    # Use pandas to read HTML table with StringIO to avoid FutureWarning
                    dfs = pd.read_html(StringIO(html_table))
                    for df in dfs:
                        # Add table identifier
                        df['table_id'] = i
                        all_dataframes.append(df)
                        self.logger.info(f"Parsed table {i} with {len(df)} rows")
                except Exception as e:
                    self.logger.warning(f"Failed to parse table {i}: {e}")

            if all_dataframes:
                # Combine all tables
                combined_df = pd.concat(all_dataframes, ignore_index=True)

                # Save as CSV
                csv_path = processing_dir / f"{document_id}_tables_combined.csv"
                combined_df.to_csv(csv_path, index=False)

                self.logger.info(f"✅ Saved {len(html_tables)} tables to CSV: {csv_path}")
            else:
                self.logger.warning("No tables could be parsed successfully")

        except Exception as e:
            self.logger.error(f"Failed to extract tables to CSV: {e}")

    def _create_processing_directory(self, document_id: str) -> Path:
        """Create unique processing directory for document."""
        processing_dir = self.temp_base_dir / document_id
        processing_dir.mkdir(parents=True, exist_ok=True)
        return processing_dir


    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract file metadata information."""
        try:
            file_stats = file_path.stat()

            return {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower().replace('.', ''),
                "file_size": file_stats.st_size,
                "page_count": 0,  # MinerU doesn't provide page count directly
                "content_length": 0  # Will be updated if markdown is available
            }

        except Exception as e:
            self.logger.warning(f"Failed to get file info: {e}")
            return {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower().replace('.', ''),
                "file_size": 0,
                "page_count": 0,
                "content_length": 0
            }

    def _error_result(self, message: str, file_path: str, error_details: str = "") -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            "status": "error",
            "error": message,
            "error_details": error_details,
            "file_path": file_path,
            "message": f"{message}: {error_details}" if error_details else message
        }