"""
DocumentProcessor - Smart document extraction with MinerU backend.
Extracts rich markdown and tables from documents using MinerU processing.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from .mu import parse_single_file
from .table_line_item_extractor import TableLineItemExtractor
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

        # Initialize table extractor
        self.table_extractor = TableLineItemExtractor(logger=self.logger)

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

            self.logger.info(f"Starting optimized MinerU extraction for: {raw_path.name}")

            # Step 1: Create clean processing directory
            processing_dir = self._create_processing_directory(document_id)

            # Step 2: Use MinerU to process document
            parse_single_file(
                file_path=raw_path,
                output_dir=str(processing_dir),
                backend="pipeline"
            )

            # Step 3: Find the generated content_list.json
            expected_output_dir = processing_dir / f"{raw_path.stem}_output"
            content_list_path = expected_output_dir / f"{raw_path.stem}_content_list.json"

            if not content_list_path.exists():
                return self._error_result("MinerU content_list.json not generated", raw_file_path)

            # Step 4: Create optimized markdown from page 0 only
            final_markdown_path = processing_dir / f"{document_id}.md"
            self._create_page0_markdown(content_list_path, final_markdown_path)

            # Step 5: Extract tables from content_list.json and save as CSV
            csv_path = processing_dir / f"{document_id}_line_items.csv"
            self.table_extractor.extract_tables_from_content_list(content_list_path, csv_path, document_id)

            # Step 6: Get file metadata
            file_info = self._get_file_info(raw_path)

            # Step 7: Clean up temporary MinerU output directory
            self._cleanup_temp_output(expected_output_dir)

            self.logger.info(f"✅ Optimized MinerU extraction completed: {final_markdown_path}")

            return {
                "status": "completed",
                "processed_markdown_path": str(final_markdown_path),
                "line_items_csv_path": str(csv_path),
                "document_id": document_id,
                "file_info": file_info,
                "processing_directory": str(processing_dir)
            }

        except Exception as e:
            self.logger.error(f"❌ Optimized MinerU extraction failed: {e}")
            return self._error_result("Extraction failed", raw_file_path, error_details=str(e))

    # HELPER FUNCTIONS

    def _create_processing_directory(self, document_id: str) -> Path:
        """Create unique processing directory for document."""
        processing_dir = self.temp_base_dir / document_id
        processing_dir.mkdir(parents=True, exist_ok=True)
        return processing_dir

    def _create_page0_markdown(self, content_list_path: Path, output_path: Path) -> None:
        """Create markdown file with only page 0 content for efficient processing."""
        try:
            with open(content_list_path, 'r', encoding='utf-8') as f:
                content_list = json.load(f)

            # Filter for page 0 content only
            page0_content = [item for item in content_list if item.get('page_idx') == 0]

            # Build markdown content
            markdown_lines = []

            for item in page0_content:
                if item.get('type') == 'text':
                    text = item.get('text', '').strip()
                    if text:
                        # Add header formatting for text_level 1
                        if item.get('text_level') == 1:
                            markdown_lines.append(f"# {text}")
                        else:
                            markdown_lines.append(text)
                        markdown_lines.append("")  # Add blank line

            # Write page 0 markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(markdown_lines))

            self.logger.info(f"Created page 0 markdown with {len(page0_content)} elements")

        except Exception as e:
            self.logger.error(f"Failed to create page 0 markdown: {e}")
            # Create empty file as fallback
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Document Processing Error\nCould not extract page 0 content.")

    def _cleanup_temp_output(self, output_dir: Path) -> None:
        """Clean up temporary MinerU output directory."""
        try:
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir)
                self.logger.info(f"Cleaned up temporary directory: {output_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory {output_dir}: {e}")


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
# python -m src.backend.doc_processing_system.pipelines.document_processing.utils.document_processor
if __name__ == "__main__":
    import datetime

    doc_processor = DocumentProcessor()
    starting = datetime.datetime.now()
    result = doc_processor.extract_document(r"C:\Users\User\Projects\scaled_processing\data\pdfs\GSPP_5407_202507_Billing.pdf", "test_doc")
    ending = datetime.datetime.now()
    print(f"Document processing completed in {(ending - starting).total_seconds()} seconds")
    print(json.dumps(result, indent=4))