"""
Table storage service orchestrator for processing table extractions.
Uses modular components to load data, detect types, manage configs, and process fields.
"""

import logging
from pathlib import Path
from typing import List

from src.backend.doc_processing_system.data_models.extraction import ExtractionResult

from .table_data_loader import TableDataLoader
from .table_config_manager import TableConfigManager
from .field_extraction_processor import FieldExtractionProcessor


class TableStorageService:
    """Main orchestrator for table extraction processing using modular components."""

    def __init__(self, config_dir: str = "data/extraction_schema_TNB"):
        """Initialize table storage service with modular components.

        Args:
            config_dir: Directory containing table extraction configurations
        """
        self.logger = logging.getLogger(__name__)

        # Initialize modular components
        self.data_loader = TableDataLoader()
        self.config_manager = TableConfigManager(config_dir)
        self.field_processor = FieldExtractionProcessor()

        self.logger.info("TableStorageService initialized with modular components")

    def process_table_extraction(
        self,
        document_id: str,
        document_name: str,
        processing_dir: Path
    ) -> List[ExtractionResult]:
        """Process table extractions from a document processing directory.

        Args:
            document_id: Unique document identifier
            document_name: Document name
            processing_dir: Directory containing table JSON files

        Returns:
            List of ExtractionResult objects ready for database storage
        """
        try:
            # Step 1: Find and load table files
            table_files = self.data_loader.find_table_files(processing_dir)
            if not table_files:
                self.logger.info(f"No table files found in {processing_dir}")
                return []

            extraction_results = []

            # Step 2: Process each table file
            for table_file in table_files:
                try:
                    results = self._process_single_table_file(
                        table_file, document_id, document_name
                    )
                    extraction_results.extend(results)

                except Exception as e:
                    self.logger.error(f"Failed to process table file {table_file}: {e}")
                    continue

            self.logger.info(f"Processed {len(extraction_results)} table extractions for {document_id}")
            return extraction_results

        except Exception as e:
            self.logger.error(f"Table extraction processing failed: {e}")
            return []

    def _process_single_table_file(
        self,
        table_file: Path,
        document_id: str,
        document_name: str
    ) -> List[ExtractionResult]:
        """Process a single table JSON file."""
        # Load table data
        tables_data = self.data_loader.load_table_data(table_file)
        if not tables_data:
            return []

        # Validate table structure
        if not self.data_loader.validate_table_structure(tables_data):
            self.logger.warning(f"Invalid table structure in {table_file}")
            return []

        # Detect document type
        doc_type = self.type_detector.detect_document_type(document_name, tables_data)

        # Load configuration
        config = self.config_manager.load_table_config(doc_type)
        if not config:
            self.logger.warning(f"No config found for document type: {doc_type}")
            return []

        # Extract fields and convert to ExtractionResults
        results = self.field_processor.extract_and_convert(
            document_id, document_name, tables_data, config
        )

        # Validate extraction results
        if results and config:
            extracted_fields = {
                result.extraction_class: result.extraction_text
                for result in results
            }
            is_valid = self.field_processor.validate_extracted_fields(extracted_fields, config)
            if not is_valid:
                self.logger.warning(f"Validation failed for {document_id}")

        return results

    def create_sample_config(self, doc_type: str = "tnb_utilities") -> bool:
        """Create a sample configuration file for testing.

        Args:
            doc_type: Document type to create config for

        Returns:
            True if config created successfully, False otherwise
        """
        return self.config_manager.create_sample_config(doc_type)

    def get_processing_summary(self, extraction_results: List[ExtractionResult]) -> dict:
        """Get summary of processing results.

        Args:
            extraction_results: List of extraction results

        Returns:
            Dictionary with processing summary
        """
        summary = self.field_processor.get_extraction_summary(extraction_results)

        # Add component information
        summary.update({
            "supported_document_types": self.type_detector.get_supported_types(),
            "cached_config_types": self.config_manager.get_cached_config_types(),
            "processing_components": [
                "TableDataLoader",
                "DocumentTypeDetector",
                "TableConfigManager",
                "FieldExtractionProcessor"
            ]
        })

        return summary

    # HELPER FUNCTIONS
    def clear_config_cache(self):
        """Clear cached configurations."""
        self.config_manager.clear_cache()
        self.logger.info("Configuration cache cleared")