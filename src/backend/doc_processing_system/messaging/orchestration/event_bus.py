"""
Central event bus for routing messages between producers and consumers.
Provides unified interface for event publishing and subscription management.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from threading import Thread, Event as ThreadEvent
from enum import Enum

from ..document_processing.document_producer import DocumentProducer
from ..extraction_pipeline.extraction_producer import ExtractionProducer
from ..query_processing.query_producer import QueryProducer


class EventType(str, Enum):
    """Types of events in the system."""
    FILE_DETECTED = "file-detected"
    DOCUMENT_AVAILABLE = "document-available"
    WORKFLOW_INITIALIZED = "workflow-initialized"
    CHUNKING_COMPLETE = "chunking-complete"
    EMBEDDING_READY = "embedding-ready"
    INGESTION_COMPLETE = "ingestion-complete"
    FIELD_INIT_COMPLETE = "field-init-complete"
    AGENT_SCALING_COMPLETE = "agent-scaling-complete"
    EXTRACTION_TASKS = "extraction-tasks"
    EXTRACTION_COMPLETE = "extraction-complete"
    QUERY_RECEIVED = "query-received"
    RAG_QUERY_COMPLETE = "rag-query-complete"
    STRUCTURED_QUERY_COMPLETE = "structured-query-complete"
    HYBRID_QUERY_COMPLETE = "hybrid-query-complete"

