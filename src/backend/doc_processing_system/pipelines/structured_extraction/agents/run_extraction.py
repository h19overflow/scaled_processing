"""
config_router.py - Orchestrates document processing using PydanticAI for structured extraction.

This module serves as the entry point for structured data extraction from document text.
It leverages an extraction_agent (PydanticAI agent) to parse and extract information
based on predefined schemas.

Dependencies:
- typing (Dict, Any)
- dotenv (load_dotenv)
- ..agents.extraction_agent (extraction_agent)
- asyncio
- logging

Role in System:
- Provides a unified process_document function for structured extraction.
- Integrates with PydanticAI agents for robust data parsing.
"""
import asyncio
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from .extraction_agent import extraction_agent

load_dotenv()
logger = logging.getLogger(__name__)


def process_document(text: str) -> Dict[str, Any]:
    """
    Processes document text using a PydanticAI agent for structured extraction.

    Args:
        text: The input document content as a string from which to extract structured data.

    Returns:
        A dictionary containing the extraction results:
        - "extractions": A list of extracted data, where each item is a dictionary
                         representing an extracted entity with its class, text, and attributes.
        - "document_id": Currently None, reserved for future use.
        - "status": "completed" if extraction was successful, "failed" otherwise.
        - "total_extractions": The number of extracted entities.

    Raises:
        Exception: Catches and logs any exceptions during the extraction process,
                   returning a failed status with an error message.
    """
    try:
        logger.info("Starting document extraction with extraction agent...")

        # Run the async extraction agent
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(extraction_agent.run(text))

        # Convert agent result to expected format
        
        extractions = result.data if hasattr(result, 'data') else []


        return {
            "extractions": extractions.to_extraction_list(),
            "document_id": None,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Document extraction failed: {e}")
        return {
            "extractions": [],
            "document_id": None,
            "status": "failed",
            "error": str(e),
            "total_extractions": 0
        }


if __name__ == "__main__":
    # Example usage with utility bill content
    text = """
ALAMAT POS
TENAGA NASIONAL BERHAD
NO. 15, JALAN SULTAN ISMAIL
50250 KUALA LUMPUR

TARIKH BIL: 15.09.2025
TEMPOH BIL: 15.08.2025 - 14.09.2025 (30 Hari)
NO. INVOIS: 000445566778
NO. AKAUN: 401234567890

Ringkasan Bil Anda:
BAKI TERDAHULU RM125.50
CAJ SEMASA RM450.00
JUMLAH BIL ANDA RM575.50

Sila bayar sebelum: 30 September 2025
Biller Code: 1234
Ref-1: 401234567890
    """
    result = process_document(text)
    print("Extraction Result:")
    print(f"Status: {result['status']}")
    print(result.get('extractions'))
