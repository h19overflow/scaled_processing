"""
Document Classification Service

Provides document type classification for structured extraction pipeline.
"""

import logging
from typing import Optional, Tuple
from pathlib import Path


class DocumentClassificationService:
    """Service for classifying document types."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def classify_document(self, content: str, filename: str = "") -> Tuple[str, float]:
        """
        Classify a document based on its content and filename.
        
        Args:
            content: Document text content
            filename: Optional filename for additional context
            
        Returns:
            Tuple of (classification, confidence_score)
        """
        # Simple heuristic-based classification for now
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        # Invoice keywords
        invoice_keywords = ['invoice', 'bill', 'payment', 'due date', 'amount due', 'subtotal']
        invoice_count = sum(1 for keyword in invoice_keywords if keyword in content_lower)
        
        # Contract keywords
        contract_keywords = ['agreement', 'contract', 'terms', 'conditions', 'party', 'whereas']
        contract_count = sum(1 for keyword in contract_keywords if keyword in content_lower)
        
        # Receipt keywords
        receipt_keywords = ['receipt', 'transaction', 'purchased', 'total', 'change']
        receipt_count = sum(1 for keyword in receipt_keywords if keyword in content_lower)
        
        # Determine classification based on keyword counts
        if invoice_count >= 2 or 'invoice' in filename_lower:
            return 'invoice', 0.8 + min(0.15, invoice_count * 0.05)
        elif contract_count >= 2 or 'contract' in filename_lower:
            return 'contract', 0.7 + min(0.15, contract_count * 0.05)  
        elif receipt_count >= 2 or 'receipt' in filename_lower:
            return 'receipt', 0.7 + min(0.15, receipt_count * 0.05)
        else:
            # Default to invoice with lower confidence
            return 'invoice', 0.6
    
    def get_supported_types(self) -> list[str]:
        """Get list of supported document types."""
        return ['invoice', 'contract', 'receipt', 'other']