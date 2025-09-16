"""
Database storage task for structured extraction results.
Processes langxtract JSON output and table extractions, stores them in the database.
"""

import uuid
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from prefect import task

from ..models.state import PipelineState
from ....core_deps.database import ExtractionCRUD, ConnectionManager
from ....data_models.extraction import ExtractionResult
from ....pipelines.document_processing.utils.table_extraction import TableStorageService

@task(name="database-storage",
      retries=2,
      retry_delay_seconds=10,
      description="Store structured extraction and table results in database.")
def store_in_database(state: PipelineState) -> dict[str, Any] | None:
    """Store extraction results and table extractions in database."""
    try:
        # Get extraction results from state
        extraction_data = getattr(state, 'extractions', None)
        if not extraction_data:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("No extraction results found in state")
            return {
                "status": "storage_skipped",
                "error": "No extraction results to store",
                "stored_count": 0
            }
        
        # Get document ID and name from state (set by config_gen task)
        document_id = getattr(state, 'document_id', None)
        document_name = getattr(state, 'document_name', None)
        
        # extraction_data should now be a list of extraction dictionaries
        if isinstance(extraction_data, list):
            extractions = extraction_data
        elif isinstance(extraction_data, dict) and 'extractions' in extraction_data:
            extractions = extraction_data['extractions']
            # Use document_id from the data if not in state
            if not document_id:
                document_id = extraction_data.get('document_id')
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected extraction data format: {type(extraction_data)}")
            return {
                "status": "storage_failed",
                "error": f"Unexpected extraction data format: {type(extraction_data)}",
                "stored_count": 0
            }
        
        if not document_id or not extractions:
            return {
                "status": "storage_skipped",
                "error": "Missing document ID or extractions",
                "stored_count": 0
            }
        
        # Use document_id as document_name if name is not provided
        if not document_name:
            document_name = document_id
        
        # Initialize database components
        connection_manager = ConnectionManager()
        extraction_crud = ExtractionCRUD(connection_manager)

        # Store structured extractions
        stored_count = 0
        stored_ids = []

        for extraction in extractions:
            try:
                # Convert document_id to proper UUID format
                uuid_document_id = _convert_to_uuid(document_id)
                result = _create_extraction_result(uuid_document_id, document_name, extraction)
                result_id = extraction_crud.create(result)
                stored_ids.append(result_id)
                stored_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to store extraction: {e}")
                continue

        # Process and store table extractions
        table_results = _process_table_extractions(state, document_id, document_name)
        for table_result in table_results:
            try:
                result_id = extraction_crud.create(table_result)
                stored_ids.append(result_id)
                stored_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to store table extraction: {e}")
                continue
        
        return {
            "status": "storage_completed",
            "stored_count": stored_count,
            "total_extractions": len(extractions),
            "stored_ids": stored_ids,
            "document_id": document_id
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database storage failed: {e}")
        return {
            "status": "storage_failed",
            "error": str(e),
            "stored_count": 0
        }

# HELPER FUNCTIONS

def _process_table_extractions(state: PipelineState, document_id: str, document_name: str) -> list[ExtractionResult]:
    """Process table extractions from state processing directory."""
    try:
        # Get processing directory from state
        processing_dir = getattr(state, 'processing_directory', None)
        if not processing_dir:
            return []

        processing_path = Path(processing_dir)
        if not processing_path.exists():
            return []

        # Initialize table storage service
        table_service = TableStorageService()

        # Process table extractions
        table_results = table_service.process_table_extraction(
            document_id, document_name, processing_path
        )

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Processed {len(table_results)} table extractions for {document_id}")

        return table_results

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to process table extractions: {e}")
        return []

def _convert_to_uuid(document_id: str) -> str:
    """Convert document_id string to a deterministic UUID format."""
    if not document_id:
        return str(uuid.uuid4())
    
    # Check if it's already a valid UUID
    try:
        uuid.UUID(document_id)
        return document_id
    except ValueError:
        # Generate a deterministic UUID from the string
        namespace = uuid.NAMESPACE_DNS
        return str(uuid.uuid5(namespace, document_id))

def _create_extraction_result(document_id: str, document_name: str, extraction: Dict[str, Any]) -> ExtractionResult:
    """Create ExtractionResult object from extraction data."""
    char_interval = extraction.get("char_interval", {})

    # Handle CharInterval object or dictionary
    if hasattr(char_interval, 'start_pos') and hasattr(char_interval, 'end_pos'):
        # It's a CharInterval object
        char_start = char_interval.start_pos
        char_end = char_interval.end_pos
    elif isinstance(char_interval, dict):
        # It's a dictionary
        char_start = char_interval.get("start_pos", 0)
        char_end = char_interval.get("end_pos", 0)
    else:
        # Fallback
        char_start = 0
        char_end = 0

    # Handle attributes - ensure it's always a dictionary, never None
    attributes = extraction.get("attributes")
    if attributes is None:
        attributes = {}
    elif not isinstance(attributes, dict):
        attributes = {}

    return ExtractionResult(
        document_id=document_id,
        document_name=document_name,
        extraction_class=extraction.get("extraction_class", "unknown"),
        extraction_text=extraction.get("extraction_text", ""),
        attributes=attributes,
        alignment_status=extraction.get("alignment_status", "unknown"),
        extraction_index=extraction.get("extraction_index", 0),
        group_index=extraction.get("group_index", 0),
        description=extraction.get("description"),
        char_start_pos=char_start,
        char_end_pos=char_end,
        timestamp=datetime.now()
    )