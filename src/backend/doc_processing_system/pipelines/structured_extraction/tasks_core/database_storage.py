"""
Database storage task for structured extraction results.
Processes langextract JSON output and stores bill data in the database.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal
from prefect import task

from ..models.state import PipelineState
from ....core_deps.database import ConnectionManager, BillModel, BillStatus

logger = logging.getLogger(__name__)


@task(name="database-storage",
      retries=2,
      retry_delay_seconds=10,
      description="Store structured extraction results in database.")
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

        # Initialize database connection
        connection_manager = ConnectionManager()

        # Create and store bill record
        try:
            bill_id = _create_and_store_bill(extractions, document_name, connection_manager)
            return {
                "status": "storage_completed",
                "stored_count": 1,
                "total_extractions": len(extractions),
                "stored_ids": [bill_id],
                "document_id": document_id
            }
        except Exception as e:
            logger.error(f"Failed to store bill: {e}")
            return {
                "status": "storage_failed",
                "error": str(e),
                "stored_count": 0
            }

    except Exception as e:
        logger.error(f"Database storage failed: {e}")
        return {
            "status": "storage_failed",
            "error": str(e),
            "stored_count": 0
        }


def _create_and_store_bill(extractions: list, document_name: str, connection_manager: ConnectionManager) -> str:
    """Create and store bill record from extractions."""
    # Map extraction fields to BillModel
    CORE_FIELDS = {'amount_due', 'due_date'}

    core_data = {}
    jsonb_data = {}

    logger.info(f"🔍 Processing {len(extractions)} extractions")

    for extraction in extractions:
        extraction_class = extraction.get('extraction_class', '')
        extraction_text = extraction.get('extraction_text', '')
        attributes = extraction.get('attributes', {})

        if extraction_class in CORE_FIELDS:
            # Process core BillModel fields
            if extraction_class == 'amount_due':
                core_data['amount_due'] = _parse_amount(attributes)
                logger.info(f"💰 Parsed amount_due: {core_data['amount_due']}")
            elif extraction_class == 'due_date':
                core_data['due_date'] = _parse_date(extraction_text, attributes)
                logger.info(f"📅 Parsed due_date: {core_data['due_date']}")
        else:
            # Store all other fields in JSONB
            jsonb_data[extraction_class] = attributes

    # Ensure required fields have defaults
    if 'amount_due' not in core_data or core_data['amount_due'] is None:
        core_data['amount_due'] = 0.0
        logger.warning("⚠️ amount_due not extracted, defaulting to 0.0")

    if 'due_date' not in core_data or core_data['due_date'] is None:
        core_data['due_date'] = datetime.now()
        logger.warning("⚠️ due_date not extracted, using current date")

    # Convert amount_due to Decimal
    amount_due_decimal = Decimal(str(core_data['amount_due']))

    logger.info(f"💾 Creating BillModel - amount_due: {amount_due_decimal}, due_date: {core_data['due_date']}")

    # Create BillModel instance
    bill = BillModel(
        document_name=document_name,
        issue_date=core_data['due_date'],  # Use due_date as issue_date for now
        due_date=core_data['due_date'],
        amount_due=amount_due_decimal,
        status=BillStatus.PENDING,
        extracted_jsonb=jsonb_data,
        version=1
    )

    # Store in database
    with connection_manager.get_session() as session:
        session.add(bill)
        session.commit()
        session.refresh(bill)
        logger.info(f"✅ Stored bill with ID: {bill.id}")
        return str(bill.id)


def _parse_date(date_text: str, attributes: dict = None) -> datetime:
    """Parse Malaysian date format to datetime."""
    if not date_text:
        return None

    # Check if ISO date is in attributes
    if attributes and 'iso_date' in attributes:
        try:
            return datetime.fromisoformat(attributes['iso_date'])
        except (ValueError, TypeError):
            pass

    # Parse Malaysian date formats
    try:
        # Format 1: DD.MM.YYYY (e.g., "01.08.2025")
        if '.' in date_text and len(date_text.split('.')) == 3:
            day, month, year = date_text.split('.')
            return datetime(int(year), int(month), int(day))

        # Format 2: DD MMM YYYY (e.g., "31 Ogos 2025")
        elif ' ' in date_text:
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mac': 3, 'Apr': 4, 'Mei': 5, 'Jun': 6,
                'Jul': 7, 'Ogos': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dis': 12,
                'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
            }

            parts = date_text.strip().split()
            if len(parts) == 3:
                day, month_str, year = parts
                month = month_map.get(month_str)
                if month:
                    return datetime(int(year), month, int(day))
    except (ValueError, IndexError):
        pass

    return None


def _parse_amount(attributes: dict = None) -> float:
    """Parse amount from attributes."""
    if attributes and 'amount_due' in attributes:
        try:
            return float(attributes['amount_due'])
        except (ValueError, TypeError):
            pass

    return 0.0
