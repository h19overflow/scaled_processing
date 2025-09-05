"""
Logging configuration for multi-agent extraction system.
Provides detailed logging across all components for debugging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """Setup comprehensive logging for the extraction system."""
    
    # Create logger
    logger = logging.getLogger("multi_agent_extraction")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def log_agent_call(logger: logging.Logger, agent_name: str, input_data: dict, step: str = "start"):
    """Log agent calls with input/output data."""
    if step == "start":
        logger.info(f"🤖 {agent_name} - Starting with input: {str(input_data)[:200]}...")
    elif step == "success":
        logger.info(f"✅ {agent_name} - Completed successfully")
    elif step == "error":
        logger.error(f"❌ {agent_name} - Failed: {input_data.get('error', 'Unknown error')}")

def log_schema_discovery(logger: logging.Logger, chunk_id: int, discovered_fields: int, total_fields: int):
    """Log schema discovery progress."""
    logger.info(f"🔍 Chunk {chunk_id}: Discovered {discovered_fields} new fields (total: {total_fields})")

def log_consolidation(logger: logging.Logger, input_fields: int, output_fields: int, document_type: str):
    """Log schema consolidation results."""
    logger.info(f"🔧 Consolidation: {input_fields} fields → {output_fields} fields | Document: {document_type}")

def log_extraction_results(logger: logging.Logger, extraction_count: int, schema_fields: int):
    """Log final extraction results."""
    logger.info(f"⚡ Extraction: {extraction_count} items extracted from {schema_fields} schema fields")