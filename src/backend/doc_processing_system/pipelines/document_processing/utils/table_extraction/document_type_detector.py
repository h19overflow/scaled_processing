"""
Document type detector for identifying document types based on filename and content.
Supports GSPP billing, TNB utilities, invoices, and general documents.
"""

import logging
from typing import Dict, List


class DocumentTypeDetector:
    """Detects document types from document names and table content."""

    def __init__(self):
        """Initialize document type detector."""
        self.logger = logging.getLogger(__name__)

    def detect_document_type(self, document_name: str, tables_data: List[Dict]) -> str:
        """Detect document type based on document name and table content.

        Args:
            document_name: Name of the document
            tables_data: List of table data dictionaries

        Returns:
            Document type string (gspp_billing, tnb_utilities, invoice, general)
        """
        doc_name_lower = document_name.lower()

        # Check filename patterns first (more reliable)
        doc_type = self._detect_from_filename(doc_name_lower)
        if doc_type != "unknown":
            self.logger.info(f"Document type detected from filename: {doc_type}")
            return doc_type

        # Fallback to content analysis
        doc_type = self._detect_from_content(tables_data)
        self.logger.info(f"Document type detected from content: {doc_type}")
        return doc_type

    def _detect_from_filename(self, doc_name_lower: str) -> str:
        """Detect document type from filename patterns."""
        # Check for GSPP billing
        if any(keyword in doc_name_lower for keyword in ['gspp', 'billing']):
            return "gspp_billing"

        # Check for TNB utilities
        if any(keyword in doc_name_lower for keyword in ['tnb', 'utilities', 'bill', 'tenaga']):
            return "tnb_utilities"

        # Check for invoice patterns
        if any(keyword in doc_name_lower for keyword in ['invoice', 'batch']):
            return "invoice"

        return "unknown"

    def _detect_from_content(self, tables_data: List[Dict]) -> str:
        """Detect document type from table content patterns."""
        if not tables_data:
            return "general"

        # Get first table for analysis
        first_table = tables_data[0] if tables_data else {}
        table_columns = first_table.get('columns', [])
        table_data = first_table.get('data', [])

        # Check for GSPP billing patterns in columns
        if self._has_gspp_billing_patterns(table_columns, table_data):
            return "gspp_billing"

        # Check for TNB utilities patterns
        if self._has_tnb_utilities_patterns(table_columns, table_data):
            return "tnb_utilities"

        # Check for invoice patterns
        if self._has_invoice_patterns(table_columns, table_data):
            return "invoice"

        return "general"

    def _has_gspp_billing_patterns(self, columns: List[str], data: List[Dict]) -> bool:
        """Check if table has GSPP billing patterns."""
        # Check columns for GSPP-specific terms
        column_text = ' '.join(str(col).lower() for col in columns)
        if 'penerangan' in column_text and 'penggunaan' in column_text:
            return True

        # Check data content for GSPP patterns
        for row in data[:3]:  # Check first few rows
            row_text = ' '.join(str(val).lower() for val in row.values() if val)
            if any(term in row_text for term in ['gspp', 'puncak', 'luar puncak']):
                return True

        return False

    def _has_tnb_utilities_patterns(self, columns: List[str], data: List[Dict]) -> bool:
        """Check if table has TNB utilities patterns."""
        # Check columns for TNB-specific terms
        column_text = ' '.join(str(col).lower() for col in columns)
        if any(term in column_text for term in ['beban', 'penggunaan', 'kwh', 'amaun']):
            return True

        # Check data content for TNB patterns
        for row in data[:3]:  # Check first few rows
            row_text = ' '.join(str(val).lower() for val in row.values() if val)
            if any(term in row_text for term in ['tnb', 'tenaga', 'beban diisytiharkan']):
                return True

        return False

    def _has_invoice_patterns(self, columns: List[str], data: List[Dict]) -> bool:
        """Check if table has invoice patterns."""
        # Check columns for invoice-specific terms
        column_text = ' '.join(str(col).lower() for col in columns)
        if any(term in column_text for term in ['invoice', 'amount', 'quantity', 'total']):
            return True

        # Check data content for invoice patterns
        for row in data[:3]:  # Check first few rows
            row_text = ' '.join(str(val).lower() for val in row.values() if val)
            if any(term in row_text for term in ['invoice', 'qty', 'unit price']):
                return True

        return False

    def get_supported_types(self) -> List[str]:
        """Get list of supported document types."""
        return ["gspp_billing", "tnb_utilities", "invoice", "general"]