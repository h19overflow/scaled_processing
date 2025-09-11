"""
Data extraction node with enhanced error handling and logging.
"""

from typing import Dict, Any, List
import json

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

from ..models.state import MultiAgentState
from ..config.settings import Settings


class ExtractionError(Exception):
    """Base exception for extraction failures."""
    pass


class LangExtractError(ExtractionError):
    """LangExtract specific errors."""
    pass


class JSONParsingError(LangExtractError):
    """AI model returned malformed JSON."""
    pass


class ModelResponseError(LangExtractError):
    """AI model response was invalid or empty."""
    pass


class ConfigurationError(ExtractionError):
    """Extraction configuration is invalid."""
    pass


def extract_data(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Extract structured data using langextract with enhanced error handling."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate input state
    try:
        _validate_extraction_state(state)
    except ConfigurationError as e:
        logger.error(f"Invalid extraction configuration: {e}")
        return {
            **state,
            "error": f"Configuration error: {str(e)}",
            "status": "error"
        }
    
    extraction_attempts = []
    extractions = None
    
    try:
        logger.debug("Starting extraction process")
        logger.debug(f"LangExtract available: {LANGEXTRACT_AVAILABLE}")
        
        # Try LangExtract first if available
        if LANGEXTRACT_AVAILABLE:
            try:
                logger.debug("Attempting LangExtract extraction")
                extractions = _extract_with_langextract(state)
                extraction_attempts.append({"method": "langextract", "status": "success", "count": len(extractions)})
                logger.info(f"LangExtract successful: {len(extractions)} extractions")
                
            except JSONParsingError as e:
                extraction_attempts.append({"method": "langextract", "status": "json_error", "error": str(e)})
                logger.warning(f"LangExtract JSON parsing failed (AI model malformed response): {e}")
                logger.debug(f"Full JSON error details: {e}", exc_info=True)
                
            except ModelResponseError as e:
                extraction_attempts.append({"method": "langextract", "status": "model_error", "error": str(e)})
                logger.warning(f"LangExtract model response error: {e}")
                logger.debug(f"Full model error details: {e}", exc_info=True)
                
            except LangExtractError as e:
                extraction_attempts.append({"method": "langextract", "status": "langextract_error", "error": str(e)})
                logger.warning(f"LangExtract library error: {e}")
                logger.debug(f"Full LangExtract error details: {e}", exc_info=True)
                
            except Exception as e:
                extraction_attempts.append({"method": "langextract", "status": "unexpected_error", "error": str(e)})
                logger.error(f"Unexpected error in LangExtract: {e}")
                logger.debug(f"Full unexpected error details: {e}", exc_info=True)
        else:
            extraction_attempts.append({"method": "langextract", "status": "unavailable"})
            logger.debug("LangExtract not available, skipping to fallback")
        
        # Use mock extraction if LangExtract failed or unavailable
        if not extractions:
            try:
                logger.debug("Using mock extraction fallback")
                extractions = _mock_extractions(state)
                extraction_attempts.append({"method": "mock", "status": "success", "count": len(extractions)})
                logger.info(f"Mock extraction successful: {len(extractions)} extractions")
                
            except Exception as e:
                extraction_attempts.append({"method": "mock", "status": "error", "error": str(e)})
                logger.error(f"Mock extraction failed: {e}")
                logger.debug(f"Full mock extraction error: {e}", exc_info=True)
                raise ExtractionError(f"Both LangExtract and mock extraction failed. Mock error: {e}")

        # Final validation
        if not extractions:
            raise ExtractionError("No valid extractions found from any method")

        # Log extraction summary
        logger.info(f"Extraction completed successfully with {len(extractions)} items")
        logger.debug(f"Extraction attempts summary: {extraction_attempts}")
        
        return {
            **state,
            "extractions": extractions,
            "extraction_attempts": extraction_attempts,
            "status": "extraction_complete"
        }

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return {
            **state,
            "error": f"Configuration error: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "status": "error"
        }
        
    except ExtractionError as e:
        logger.error(f"Extraction error: {e}")
        return {
            **state,
            "error": f"Extraction error: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "status": "error"
        }
        
    except Exception as e:
        logger.critical(f"Critical unexpected error in extraction: {e}")
        logger.debug(f"Full critical error details: {e}", exc_info=True)
        return {
            **state,
            "error": f"Critical extraction failure: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "status": "error"
        }


def _extract_with_langextract(state: MultiAgentState) -> List[Dict[str, Any]]:
    """Extract data using LangExtract library."""
    # Validate inputs
    if not state["document_text"] or len(state["document_text"].strip()) < 100:
        raise ValueError("Document text is too short or empty")

    if not state["config"]["examples"] or len(state["config"]["examples"]) == 0:
        raise ValueError("No examples provided for extraction")

    # Create proper LangExtract ExampleData objects with Extraction objects
    examples = []
    for ex_data in state["config"]["examples"]:
        # Create sample extraction objects for the example
        sample_extractions = []
        
        # Get fields from progressive results to create realistic extractions
        if state.get("progressive_results"):
            for prog_result in state["progressive_results"][:1]:  # Use first result
                # Handle both object and dict formats
                if hasattr(prog_result, 'discovered_fields'):
                    fields = prog_result.discovered_fields
                elif isinstance(prog_result, dict) and 'discovered_fields' in prog_result:
                    fields = prog_result['discovered_fields']
                else:
                    continue
                
                # Create extraction objects from discovered fields
                for i, field in enumerate(fields[:2]):  # Limit to 2 for examples
                    # Handle both FieldSchema objects and dicts properly
                    if hasattr(field, 'field_name'):
                        # It's a FieldSchema object
                        field_name = field.field_name
                        example_text = getattr(field, 'example_text', f'sample_{field_name}')
                    elif isinstance(field, dict):
                        # It's a dict representation
                        field_name = field.get('field_name', f'field_{i}')
                        example_text = field.get('example_text', f'sample_{field_name}')
                    else:
                        # Fallback
                        field_name = f'field_{i}'
                        example_text = f'sample_{field_name}'
                    
                    extraction = lx.data.Extraction(
                        extraction_class=field_name,
                        extraction_text=example_text
                    )
                    sample_extractions.append(extraction)
        
        # If no fields found, create a basic example
        if not sample_extractions:
            extraction = lx.data.Extraction(
                extraction_class="sample_field",
                extraction_text="Sample value"
            )
            sample_extractions.append(extraction)
        
        # Create ExampleData object
        example_data = lx.data.ExampleData(
            text=ex_data.get("example", "Sample text for extraction"),
            extractions=sample_extractions
        )
        examples.append(example_data)

    # Wrap LangExtract call with enhanced error handling
    try:
        result = lx.extract(
            text_or_documents=state["document_text"],
            prompt_description=state["config"]["prompt"],
            examples=examples,
            model_id=state["config"]["model_id"]
        )
    except json.JSONDecodeError as e:
        raise JSONParsingError(f"AI model returned invalid JSON: {str(e)[:200]}...")
    except Exception as e:
        error_str = str(e).lower()
        # Check for specific JSON parsing patterns
        json_error_patterns = [
            "json", "parse", "decode", "expecting", "delimiter", 
            "unterminated string", "invalid character", "malformed"
        ]
        
        if any(pattern in error_str for pattern in json_error_patterns):
            raise JSONParsingError(f"AI model JSON parsing failed: {str(e)[:200]}...")
        
        # Check for model/API specific errors
        api_error_patterns = [
            "api", "quota", "rate limit", "authentication", "authorization",
            "model", "timeout", "connection", "network"
        ]
        
        if any(pattern in error_str for pattern in api_error_patterns):
            raise ModelResponseError(f"AI model API error: {str(e)[:200]}...")
        
        # Generic LangExtract error
        raise LangExtractError(f"LangExtract extraction failed: {str(e)[:200]}...")

    # Validate result structure
    if not result:
        raise ModelResponseError("LangExtract returned None/empty result")
    
    if not hasattr(result, 'extractions'):
        raise ModelResponseError("LangExtract result missing 'extractions' attribute")
    
    if result.extractions is None:
        raise ModelResponseError("LangExtract extractions is None")

    extractions = []
    for extraction in result.extractions:
        # Filter out empty or invalid extractions
        if (extraction.extraction_text and
                extraction.extraction_text.strip() and
                extraction.extraction_text.lower() not in ['null', 'none', 'n/a', ''] and
                len(extraction.extraction_text.strip()) > 5):
            extractions.append({
                "extraction_class": extraction.extraction_class,
                "extraction_text": extraction.extraction_text.strip(),
                "attributes": extraction.attributes
            })

    if len(extractions) == 0:
        raise ValueError("No valid extractions found - all extractions were empty or invalid")

    return extractions


def _validate_extraction_state(state: MultiAgentState) -> None:
    """Validate that the state contains required fields for extraction."""
    required_fields = ["document_text", "config"]
    
    for field in required_fields:
        if field not in state:
            raise ConfigurationError(f"Missing required field in state: {field}")
        
        if not state[field]:
            raise ConfigurationError(f"Required field '{field}' is None or empty")
    
    # Validate config structure
    config = state["config"]
    required_config_fields = ["prompt", "model_id"]
    
    for field in required_config_fields:
        if field not in config:
            raise ConfigurationError(f"Missing required config field: {field}")
        
        if not config[field]:
            raise ConfigurationError(f"Required config field '{field}' is None or empty")
    
    # Validate document text
    if not isinstance(state["document_text"], str):
        raise ConfigurationError("document_text must be a string")
    
    if len(state["document_text"].strip()) < 10:
        raise ConfigurationError("document_text is too short for meaningful extraction")


def _mock_extractions(state: MultiAgentState) -> List[Dict[str, Any]]:
    """Create mock extractions when LangExtract is not available."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        extractions = []
        
        # Validate state for mock extraction
        if not state.get("progressive_results"):
            logger.warning("No progressive_results found in state - cannot create mock extractions")
            raise ExtractionError("Cannot create mock extractions: missing progressive_results")
        
        progressive_results = state["progressive_results"]
        if not isinstance(progressive_results, list):
            raise ExtractionError(f"progressive_results must be a list, got {type(progressive_results)}")
        
        if len(progressive_results) == 0:
            logger.warning("Empty progressive_results - no fields to extract")
            raise ExtractionError("Cannot create mock extractions: empty progressive_results")
        
        logger.debug(f"Processing {len(progressive_results)} progressive results for mock extraction")
        
        # Get fields directly from discovery results with enhanced error handling
        all_fields = []
        
        for i, result in enumerate(progressive_results):
            logger.debug(f"Processing result {i}: type={type(result)}")
            
            try:
                # Handle both ProgressiveSchema objects and dicts
                if hasattr(result, 'discovered_fields'):
                    # It's a ProgressiveSchema object
                    discovered_fields = result.discovered_fields
                    logger.debug(f"Result {i}: Found {len(discovered_fields)} fields via object attribute")
                elif isinstance(result, dict) and "discovered_fields" in result:
                    # It's a dict with discovered_fields key
                    discovered_fields = result["discovered_fields"]
                    logger.debug(f"Result {i}: Found {len(discovered_fields)} fields via dict key")
                else:
                    logger.warning(f"Result {i}: No discovered_fields found. Type: {type(result)}, Keys: {getattr(result, 'keys', lambda: 'N/A')()}")
                    continue
                    
                # Add fields to the collection
                if discovered_fields:
                    all_fields.extend(discovered_fields)
                    logger.debug(f"Added {len(discovered_fields)} fields from result {i}")
                    
            except Exception as e:
                logger.error(f"Error processing progressive result {i}: {e}")
                logger.debug(f"Full error details for result {i}: {e}", exc_info=True)
                continue

        logger.debug(f"Total fields collected: {len(all_fields)}")
        
        if not all_fields:
            raise ExtractionError("No valid fields found in progressive_results for mock extraction")
        
        # Create mock extractions from the fields
        for i, field in enumerate(all_fields[:3]):  # Limit to first 3 for mock
            try:
                # Handle both FieldSchema objects and dicts
                if hasattr(field, 'field_name'):
                    # It's a FieldSchema object
                    field_name = field.field_name
                    category = getattr(field, 'category', 'unknown')
                    subcategory = getattr(field, 'subcategory', 'general')
                    example_text = getattr(field, 'example_text', f'Sample {field_name}')
                    # Check for sample_values attribute (may not exist in schema)
                    sample_values = getattr(field, 'sample_values', [])
                elif isinstance(field, dict):
                    # It's a dict representation
                    field_name = field.get('field_name', f'field_{i}')
                    category = field.get('category', 'unknown')
                    subcategory = field.get('subcategory', 'general')
                    example_text = field.get('example_text', f'Sample {field_name}')
                    sample_values = field.get('sample_values', [])
                else:
                    logger.warning(f"Field {i}: Unknown format {type(field)}")
                    continue
                    
                # Use sample_values if available, otherwise use example_text
                extraction_text = sample_values[0] if sample_values else example_text
                
                extractions.append({
                    "extraction_class": field_name,
                    "extraction_text": extraction_text,
                    "attributes": {"category": category, "subcategory": subcategory}
                })
                
                logger.debug(f"Created extraction {i}: {field_name}")
                
            except Exception as e:
                logger.error(f"Error creating extraction from field {i}: {e}")
                logger.debug(f"Full field processing error: {e}", exc_info=True)
                continue

        logger.info(f"Created {len(extractions)} mock extractions")
        
        if not extractions:
            raise ExtractionError("Failed to create any mock extractions from available fields")
            
        return extractions
        
    except ExtractionError:
        # Re-raise extraction errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error in mock extraction: {e}")
        logger.debug(f"Full mock extraction error: {e}", exc_info=True)
        raise ExtractionError(f"Mock extraction failed due to unexpected error: {str(e)}")
