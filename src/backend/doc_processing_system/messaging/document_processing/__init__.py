"""
Document processing messaging components.
Handles document-received events and workflow coordination.
"""

from .document_producer import DocumentProducer

__all__ = [
    "DocumentProducer",
    "create_simple_document_consumer",
    "log_document_filename"
]