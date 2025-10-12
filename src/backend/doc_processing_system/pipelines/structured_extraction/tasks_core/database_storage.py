"""
Database storage task for structured extraction results.
Processes langextract JSON output and stores bill data in the database.
"""

import logging
import decimal
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from ..models.state import PipelineState
from ....core_deps.database import ConnectionManager, BillStatus
from ....core_deps.database.CRUD.bill_CRUD import BillCRUD

logger = logging.getLogger(__name__)


def store_in_database(state: PipelineState) -> dict[str, Any] | None:
    """Store extraction results in database."""
    try:
        # Get extraction results from state
        extraction_data = getattr(state, 'extractions', None)
        if not extraction_data:
            logger.warning("No extraction results found in state")
            return {
                "status": "storage_skipped",
                "error": "No extraction results to store",
                "stored_count": 0
            }

        # Get document ID and name from state
        document_id = getattr(state, 'document_id', None)
        document_name = getattr(state, 'document_name', None)

        logger.info(f"📋 Storage - document_id: '{document_id}', document_name: '{document_name}'")

        # Normalize extraction_data to list
        if isinstance(extraction_data, list):
            extractions = extraction_data
        elif isinstance(extraction_data, dict) and 'extractions' in extraction_data:
            extractions = extraction_data['extractions']
            if not document_id:
                document_id = extraction_data.get('document_id')
        else:
            logger.error(f"Unexpected extraction data format: {type(extraction_data)}")
            return {
                "status": "storage_error",
                "error": f"Unexpected extraction data format: {type(extraction_data)}",
                "stored_count": 0
            }

        if not document_id or not extractions:
            return {
                "status": "storage_skipped",
                "error": "Missing document ID or extractions",
                "stored_count": 0
            }

        # Validate document_name exists
        if not document_name:
            logger.error(f"Missing document_name for document_id: {document_id}")
            return {
                "status": "storage_error",
                "error": f"Missing document_name for document_id: {document_id}",
                "stored_count": 0
            }

        # Initialize database connection
        connection_manager = ConnectionManager()

        # Check if bill already exists for this document (by document_id)
        bill_crud = BillCRUD(connection_manager)
        existing_bill_id = bill_crud.get_bill_by_document_id(document_id)

        if existing_bill_id:
            logger.info(f"Duplicate detected: Bill already exists for document_id '{document_id}' (document: '{document_name}') with ID: {existing_bill_id}")
            return {
                "status": "storage_skipped",
                "error": f"Bill already exists for document_id '{document_id}'",
                "stored_count": 0,
                "existing_bill_id": existing_bill_id,
                "document_id": document_id
            }

        # Create and store bill record
        try:
            bill_id = _create_and_store_bill(extractions, document_name, document_id, connection_manager)
            return {
                "status": "storage_completed",
                "stored_count": 1,
                "total_extractions": len(extractions),
                "stored_ids": [bill_id],
                "document_id": document_id
            }
        except IntegrityError as e:
            # Unique constraint violation - duplicate document_name (race condition)
            logger.info(f"Duplicate bill detected (race condition): document '{document_name}' already exists")
            return {
                "status": "storage_skipped",
                "error": f"Bill already exists for document '{document_name}' (race condition)",
                "stored_count": 0,
                "document_id": document_id
            }
        except Exception as e:
            logger.error(f"Failed to store bill: {e}")
            return {
                "status": "storage_error",
                "error": str(e),
                "stored_count": 0
            }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Database storage failed: {e}")
        logger.error(f"Full traceback:\n{error_trace}")
        return {
            "status": "storage_error",
            "error": f"{str(e)} | Traceback: {error_trace}",
            "stored_count": 0
        }


def _create_and_store_bill(extractions: list, document_name: str, document_id: str, connection_manager: ConnectionManager) -> str:
    """Create and store bill record from extractions."""
    # Map extraction fields to BillModel
    CORE_FIELDS = {'amount_due', 'due_date', 'issue_date'}

    core_data = {}
    jsonb_data = {
        'document_id': document_id  # Store document_id for duplicate checking
    }

    logger.info(f"🔍 Processing {len(extractions)} extractions")
    logger.info(f"📋 Raw extractions data: {extractions}")

    for extraction in extractions:
        extraction_class = extraction.get('extraction_class', '')
        extraction_text = extraction.get('extraction_text', '')
        attributes = extraction.get('attributes', {})
        
        logger.info(f"Processing extraction: class={extraction_class}, text='{extraction_text}', attributes={attributes}")

        if extraction_class in CORE_FIELDS:
            # Process core BillModel fields
            if extraction_class == 'amount_due':
                parsed_amount = _parse_amount(attributes)
                if parsed_amount is not None:
                    core_data['amount_due'] = parsed_amount
                    logger.info(f"💰 Parsed amount_due: {core_data['amount_due']}")
                else:
                    logger.warning(f"⚠️ Failed to parse amount_due from attributes: {attributes}")
            elif extraction_class == 'due_date':
                parsed_date = _parse_date(extraction_text, attributes)
                if parsed_date is not None:
                    core_data['due_date'] = parsed_date
                    logger.info(f"📅 Parsed due_date: {core_data['due_date']}")
                else:
                    logger.warning(f"⚠️ Failed to parse due_date from text: '{extraction_text}', attributes: {attributes}")
            elif extraction_class == 'issue_date':
                parsed_date = _parse_date(extraction_text, attributes)
                if parsed_date is not None:
                    core_data['issue_date'] = parsed_date
                    logger.info(f"📅 Parsed issue_date: {core_data['issue_date']}")
                else:
                    logger.warning(f"⚠️ Failed to parse issue_date from text: '{extraction_text}', attributes: {attributes}")
        else:
            # Store all other fields in JSONB
            jsonb_data[extraction_class] = attributes
            logger.info(f"📦 Added to JSONB: {extraction_class} = {attributes}")
    
    logger.info(f"📊 Final core_data: {core_data}")
    logger.info(f"📦 Final jsonb_data: {jsonb_data}")

    # Ensure required fields have defaults
    if 'amount_due' not in core_data or core_data['amount_due'] is None:
        core_data['amount_due'] = 0.0
        logger.warning("⚠️ amount_due not extracted, defaulting to 0.0")

    if 'due_date' not in core_data or core_data['due_date'] is None:
        core_data['due_date'] = datetime.now()
        logger.warning("⚠️ due_date not extracted, using current date")
    
    # Handle issue_date - use issue_date if available, otherwise fall back to due_date
    if 'issue_date' not in core_data or core_data['issue_date'] is None:
        core_data['issue_date'] = core_data['due_date']
        logger.info(f"📅 Using due_date as issue_date: {core_data['issue_date']}")

    # Convert amount_due to Decimal with error handling
    try:
        amount_due_decimal = Decimal(str(core_data['amount_due']))
    except (ValueError, TypeError, decimal.InvalidOperation) as e:
        logger.error(f"Failed to convert amount_due to Decimal: {e}, using 0.00")
        amount_due_decimal = Decimal('0.00')

    logger.info(f"💾 Creating BillModel - amount_due: {amount_due_decimal}, issue_date: {core_data['issue_date']}, due_date: {core_data['due_date']}")

    # Create BillModel instance
   

        # Store in database
    bill_id = BillCRUD(connection_manager).create(document_name=document_name,
                                                  issue_date=core_data['issue_date'],
                                                  due_date=core_data['due_date'], 
                                                  amount_due=amount_due_decimal, 
                                                  status=BillStatus.PENDING, 
                                                  extracted_jsonb=jsonb_data, 
                                                  version=1)
    logger.info(f"✅ Stored bill with ID: {bill_id}")
    return str(bill_id)


def _parse_date(date_text: str, attributes: dict = None) -> Optional[datetime]:
    """Parse Malaysian date format to datetime with robust error handling."""
    if not date_text:
        return None

    # Check if ISO date is in attributes first (most reliable)
    if attributes and 'iso_date' in attributes:
        try:
            iso_date = attributes['iso_date']
            if iso_date:
                return datetime.fromisoformat(iso_date)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse ISO date '{attributes.get('iso_date')}': {e}")

    # Parse Malaysian date formats from text
    try:
        # Clean the date text
        date_text = date_text.strip()
        
        # Format 1: DD.MM.YYYY (e.g., "01.08.2025")
        if '.' in date_text and len(date_text.split('.')) == 3:
            day, month, year = date_text.split('.')
            return datetime(int(year), int(month), int(day))

        # Format 2: DD MMM YYYY (e.g., "31 Ogos 2025", "30 September 2025")
        elif ' ' in date_text:
            month_map = {
                # Malay months
                'Jan': 1, 'Feb': 2, 'Mac': 3, 'Apr': 4, 'Mei': 5, 'Jun': 6,
                'Jul': 7, 'Ogos': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dis': 12,
                # English months (full and abbreviated)
                'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12,
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }

            parts = date_text.strip().split()
            if len(parts) == 3:
                day, month_str, year = parts
                month = month_map.get(month_str)
                if month:
                    return datetime(int(year), month, int(day))
                else:
                    logger.warning(f"Unknown month name: {month_str}")
        
        # Format 3: YYYY-MM-DD (ISO format)
        elif '-' in date_text and len(date_text.split('-')) == 3:
            year, month, day = date_text.split('-')
            return datetime(int(year), int(month), int(day))
            
    except (ValueError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse date '{date_text}': {e}")

    return None


def _parse_amount(attributes: dict = None) -> Optional[float]:
    """Parse amount from attributes with robust error handling."""
    if not attributes:
        return None
        
    if 'amount_due' in attributes:
        try:
            amount = attributes['amount_due']
            if amount is None:
                return None
            
            # Handle string amounts with commas
            if isinstance(amount, str):
                # Remove commas and RM prefix if present
                amount = amount.replace(',', '').replace('RM', '').strip()
                
            return float(amount)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse amount '{attributes.get('amount_due')}': {e}")

    return None
