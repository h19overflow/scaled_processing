import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .extraction_agent import extraction_agent
load_dotenv()



def process_document(text: str) -> Dict[str, Any]:
    """Process document using PydanticAI agent with Gemini 2.0 Flash"""
    import asyncio
    import logging
    import threading

    logger = logging.getLogger(__name__)

    def run_with_new_loop():
        """Run extraction with a fresh event loop"""
        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)

            async def extract():
                result = await extraction_agent.run(text)
                return result.data.to_extraction_list()

            extraction_list = loop.run_until_complete(extract())

            return {
                "extractions": extraction_list,
                "document_id": None,
                "status": "completed",
                "total_extractions": len(extraction_list)
            }

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {
                "extractions": [],
                "document_id": None,
                "status": "failed",
                "error": str(e),
                "total_extractions": 0
            }
        finally:
            try:
                loop.close()
            except:
                pass
            try:
                asyncio.set_event_loop(None)
            except:
                pass

    try:
        logger.info("Starting document extraction...")

        # Check if we're in a worker thread (e.g., Prefect)
        # Main thread is typically named "MainThread", worker threads have different names
        is_worker_thread = threading.current_thread().name != "MainThread"

        # Detect if there's already a running event loop in this thread
        try:
            running_loop = asyncio.get_running_loop()
            has_running_loop = True
        except RuntimeError:
            has_running_loop = False

        # Use new loop approach if:
        # 1. We're in a worker thread (likely no event loop), OR
        # 2. There's already a running loop (can't use run_sync)
        if is_worker_thread or has_running_loop:
            logger.debug(f"Using new event loop approach (worker_thread={is_worker_thread}, has_running_loop={has_running_loop})")
            return run_with_new_loop()

        # Otherwise, try run_sync for simpler execution
        try:
            result = extraction_agent.run_sync(text)
            extraction_list = result.data.to_extraction_list()

            return {
                "extractions": extraction_list,
                "document_id": None,
                "status": "completed",
                "total_extractions": len(extraction_list)
            }

        except RuntimeError as sync_error:
            if "event loop" in str(sync_error).lower():
                logger.debug(f"run_sync failed, using new loop: {sync_error}")
                return run_with_new_loop()
            else:
                raise sync_error

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
    print(f"Total extractions: {result['total_extractions']}")
    print("\nExtractions:")
    for extraction in result['extractions']:
        print(f"- {extraction['extraction_class']}: {extraction['extraction_text']}")
        print(f"  Attributes: {extraction['attributes']}")
        print()