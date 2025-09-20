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
from ....core_deps.database import ExtractionCRUD, ConnectionManager, BillModel, BillStatus
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

        # Store bill data directly
        stored_count = 0
        stored_ids = []

        try:
            # Create bill record from extractions
            bill_id = _create_and_store_bill(extractions, document_id, document_name, connection_manager)
            if bill_id:
                stored_ids.append(bill_id)
                stored_count = 1
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to store bill: {e}")

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

def _create_and_store_bill(extractions: list, document_id: str, document_name: str, connection_manager: ConnectionManager) -> str:
    """Create and store bill record from extractions."""
    # Define core fields that map to BillModel columns
    BILL_CORE_FIELDS = {
        'bill_account_id': 'bill_account_id',
        'billing_period_start': 'billing_period_start',
        'billing_period_end': 'billing_period_end',
        'issue_date': 'issue_date',
        'due_date': 'due_date',
        'currency': 'currency',
        'amount_due': 'amount_due'
    }

    # Extract core fields and remaining fields
    core_data = {}
    jsonb_data = {}

    for extraction in extractions:
        extraction_class = extraction.get('extraction_class', '')
        extraction_text = extraction.get('extraction_text', '')
        attributes = extraction.get('attributes', {})

        if extraction_class in BILL_CORE_FIELDS:
            # Map to core BillModel field
            if extraction_class == 'bill_account_id':
                core_data['bill_account_id'] = _account_to_uuid(extraction_text)
                # Preserve original account number in jsonb
                jsonb_data['account_number'] = extraction_text
            elif extraction_class == 'billing_period_start':
                core_data['billing_period_start'] = _parse_billing_period_start(extraction_text, attributes)
            elif extraction_class == 'billing_period_end':
                core_data['billing_period_end'] = _parse_billing_period_end(extraction_text, attributes)
            elif extraction_class in ['issue_date', 'due_date']:
                core_data[extraction_class] = _parse_malaysian_date(extraction_text, attributes)
            elif extraction_class == 'amount_due':
                core_data['amount_due'] = _parse_amount(extraction_text, attributes)
            elif extraction_class == 'currency':
                core_data['currency'] = _extract_currency(extraction_text, attributes)
        else:
            # Add to jsonb data - store only attributes for clean structure
            jsonb_data[extraction_class] = attributes

    # Set defaults for missing core fields
    if 'currency' not in core_data:
        core_data['currency'] = 'MYR'

    # Create BillModel instance
    bill = BillModel(
        bill_account_id=core_data.get('bill_account_id'),
        billing_period_start=core_data.get('billing_period_start'),
        billing_period_end=core_data.get('billing_period_end'),
        issue_date=core_data.get('issue_date'),
        due_date=core_data.get('due_date'),
        currency=core_data.get('currency', 'MYR'),
        amount_due=core_data.get('amount_due'),
        status=BillStatus.PENDING,
        extracted_jsonb=jsonb_data,
        version=1
    )

    # Store in database
    with connection_manager.get_session() as session:
        session.add(bill)
        session.commit()
        session.refresh(bill)
        return str(bill.id)

def _account_to_uuid(account_number: str) -> str:
    """Convert account number to UUID."""
    if not account_number:
        return str(uuid.uuid4())

    try:
        # Check if already a UUID
        uuid.UUID(account_number)
        return account_number
    except ValueError:
        # Generate deterministic UUID from account number
        namespace = uuid.NAMESPACE_DNS
        return str(uuid.uuid5(namespace, account_number))

def _parse_malaysian_date(date_text: str, attributes: dict = None) -> datetime:
    """Parse Malaysian date format to datetime."""
    if not date_text:
        return None

    # Check if ISO date is in attributes
    if attributes and 'iso_date' in attributes:
        try:
            return datetime.fromisoformat(attributes['iso_date'])
        except:
            pass

    # Parse Malaysian format like "01.08.2025"
    try:
        if '.' in date_text:
            # Format: DD.MM.YYYY
            day, month, year = date_text.split('.')
            return datetime(int(year), int(month), int(day))
        elif '-' in date_text and ' - ' in date_text:
            # Handle period ranges, extract start date
            start_date = date_text.split(' - ')[0]
            day, month, year = start_date.split('.')
            return datetime(int(year), int(month), int(day))
    except:
        pass

    return None

def _parse_amount(amount_text: str, attributes: dict = None) -> float:
    """Parse amount from text or attributes."""
    if attributes and 'amount' in attributes:
        try:
            return float(attributes['amount'])
        except:
            pass

    if not amount_text:
        return None

    # Remove currency symbols and commas
    cleaned = amount_text.replace('RM', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except:
        return None

def _extract_currency(currency_text: str, attributes: dict = None) -> str:
    """Extract currency from text or attributes."""
    if attributes and 'currency' in attributes:
        currency = attributes['currency']
        if currency == 'MYR' or currency == 'RM':
            return 'MYR'

    if 'RM' in currency_text or 'MYR' in currency_text:
        return 'MYR'

    return 'MYR'  # Default for Malaysian bills

def _parse_billing_period_start(date_text: str, attributes: dict = None) -> datetime:
    """Parse billing period start date."""
    if not date_text or date_text.strip() == "":
        return None

    # Check for start_date in attributes first
    if attributes and 'start_date' in attributes and attributes['start_date']:
        try:
            return datetime.fromisoformat(attributes['start_date'])
        except:
            pass

    # Fallback to general date parsing
    return _parse_malaysian_date(date_text, attributes)

def _parse_billing_period_end(date_text: str, attributes: dict = None) -> datetime:
    """Parse billing period end date."""
    if not date_text or date_text.strip() == "":
        return None

    # Check for end_date in attributes first
    if attributes and 'end_date' in attributes and attributes['end_date']:
        try:
            return datetime.fromisoformat(attributes['end_date'])
        except:
            pass

    # Fallback to general date parsing
    return _parse_malaysian_date(date_text, attributes)

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
        alignment_status=extraction.get("alignment_status") or "unknown",
        extraction_index=extraction.get("extraction_index", 0),
        group_index=extraction.get("group_index", 0),
        description=extraction.get("description") or "",
        char_start_pos=char_start,
        char_end_pos=char_end,
        timestamp=datetime.now()
    )