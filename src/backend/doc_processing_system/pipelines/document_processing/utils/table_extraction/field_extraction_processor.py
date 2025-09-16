"""
Field extraction processor for converting table data to ExtractionResult objects.
Handles field extraction using configurations and result formatting.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.backend.doc_processing_system.data_models.table_extraction import (
    TableExtractionConfig,
    TableExtractionResult
)
from src.backend.doc_processing_system.data_models.extraction import ExtractionResult


class FieldExtractionProcessor:
    """Processes field extraction and converts to database format."""

    def __init__(self):
        """Initialize field extraction processor."""
        self.logger = logging.getLogger(__name__)

    def extract_and_convert(
        self,
        document_id: str,
        document_name: str,
        tables_data: List[Dict],
        config: TableExtractionConfig
    ) -> List[ExtractionResult]:
        """Extract configured fields and convert to ExtractionResult objects.

        Args:
            document_id: Unique document identifier
            document_name: Document name
            tables_data: List of table data dictionaries
            config: Table extraction configuration

        Returns:
            List of ExtractionResult objects ready for database storage
        """
        try:
            # Extract all fields using the configuration
            extracted_fields = config.extract_all_fields(tables_data)

            if not extracted_fields:
                self.logger.warning(f"No fields extracted for {document_id}")
                return []

            # Create table extraction result
            table_result = self._create_table_result(
                document_id, document_name, extracted_fields, config, tables_data
            )

            # Convert to ExtractionResult format
            extraction_dicts = table_result.to_extraction_results()

            # Convert to ExtractionResult objects
            extraction_results = self._convert_to_extraction_results(
                document_id, document_name, extraction_dicts
            )

            self.logger.info(f"Converted {len(extraction_results)} field extractions for {document_id}")
            return extraction_results

        except Exception as e:
            self.logger.error(f"Failed to extract and convert fields: {e}")
            return []

    def _create_table_result(
        self,
        document_id: str,
        document_name: str,
        extracted_fields: Dict[str, Any],
        config: TableExtractionConfig,
        tables_data: List[Dict]
    ) -> TableExtractionResult:
        """Create TableExtractionResult object."""
        return TableExtractionResult(
            document_id=document_id,
            document_name=document_name,
            table_extractions=extracted_fields,
            extraction_config=config.document_type,
            tables_count=len(tables_data),
            timestamp=datetime.now()
        )

    def _convert_to_extraction_results(
        self,
        document_id: str,
        document_name: str,
        extraction_dicts: List[Dict[str, Any]]
    ) -> List[ExtractionResult]:
        """Convert extraction dictionaries to ExtractionResult objects."""
        extraction_results = []

        for extraction_dict in extraction_dicts:
            try:
                result = ExtractionResult(
                    document_id=document_id,
                    document_name=document_name,
                    extraction_class=extraction_dict['extraction_class'],
                    extraction_text=extraction_dict['extraction_text'],
                    attributes=extraction_dict['attributes'],
                    alignment_status=extraction_dict['alignment_status'],
                    extraction_index=extraction_dict['extraction_index'],
                    group_index=extraction_dict['group_index'],
                    description=extraction_dict['description'],
                    char_start_pos=extraction_dict['char_start_pos'],
                    char_end_pos=extraction_dict['char_end_pos'],
                    timestamp=datetime.now()
                )
                extraction_results.append(result)

            except Exception as e:
                self.logger.error(f"Failed to create ExtractionResult: {e}")
                continue

        return extraction_results

    def validate_extracted_fields(self, extracted_fields: Dict[str, Any], config: TableExtractionConfig) -> bool:
        """Validate extracted fields against configuration requirements.

        Args:
            extracted_fields: Dictionary of extracted field values
            config: Table extraction configuration

        Returns:
            True if validation passes, False otherwise
        """
        required_fields = config.get_required_fields()

        for field_name in required_fields:
            if field_name not in extracted_fields:
                self.logger.error(f"Required field missing: {field_name}")
                return False

            value = extracted_fields[field_name]
            if value is None or value == "":
                self.logger.error(f"Required field has empty value: {field_name}")
                return False

        self.logger.info(f"Validation passed for {len(extracted_fields)} extracted fields")
        return True

    def get_extraction_summary(self, extraction_results: List[ExtractionResult]) -> Dict[str, Any]:
        """Get summary statistics for extraction results.

        Args:
            extraction_results: List of extraction results

        Returns:
            Dictionary with summary statistics
        """
        if not extraction_results:
            return {"total_extractions": 0, "extraction_classes": []}

        extraction_classes = list(set(result.extraction_class for result in extraction_results))

        return {
            "total_extractions": len(extraction_results),
            "extraction_classes": extraction_classes,
            "class_counts": {
                cls: sum(1 for r in extraction_results if r.extraction_class == cls)
                for cls in extraction_classes
            },
            "document_ids": list(set(result.document_id for result in extraction_results))
        }