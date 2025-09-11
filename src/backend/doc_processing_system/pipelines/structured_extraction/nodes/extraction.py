"""
Data extraction node with enhanced error handling and logging.
"""

from typing import Dict, Any, List
import json
import logging

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
        
        # Create comprehensive intermediate results
        intermediate_results = _create_intermediate_results(
            extractions, 
            extraction_attempts, 
            state, 
            settings
        )
        
        return {
            **state,
            "extractions": extractions,
            "extraction_attempts": extraction_attempts,
            "intermediate_results": intermediate_results,
            "status": "extraction_complete"
        }

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        # Create intermediate results even for failures
        intermediate_results = _create_intermediate_results(
            [], extraction_attempts, state, settings
        )
        return {
            **state,
            "error": f"Configuration error: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "intermediate_results": intermediate_results,
            "status": "error"
        }
        
    except ExtractionError as e:
        logger.error(f"Extraction error: {e}")
        # Create intermediate results even for failures
        intermediate_results = _create_intermediate_results(
            [], extraction_attempts, state, settings
        )
        return {
            **state,
            "error": f"Extraction error: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "intermediate_results": intermediate_results,
            "status": "error"
        }
        
    except Exception as e:
        logger.critical(f"Critical unexpected error in extraction: {e}")
        logger.debug(f"Full critical error details: {e}", exc_info=True)
        # Create intermediate results even for critical failures
        intermediate_results = _create_intermediate_results(
            [], extraction_attempts, state, settings
        )
        return {
            **state,
            "error": f"Critical extraction failure: {str(e)}",
            "extraction_attempts": extraction_attempts,
            "intermediate_results": intermediate_results,
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

    # Enhanced pre-call logging and validation
    import logging
    logger = logging.getLogger(__name__)
    
    # Log all parameters before LangExtract call
    logger.debug("LangExtract inputs validation:")
    logger.debug(f"  document_text length: {len(state['document_text'])}")
    logger.debug(f"  document_text preview: {state['document_text'][:200]}...")
    logger.debug(f"  prompt length: {len(state['config']['prompt'])}")
    logger.debug(f"  prompt content: {state['config']['prompt'][:300]}...")
    logger.debug(f"  model_id: {state['config']['model_id']}")
    logger.debug(f"  examples count: {len(examples)}")
    
    # Final input sanitization
    document_text = state["document_text"].strip()
    prompt_description = state["config"]["prompt"].strip()
    model_id = state["config"]["model_id"].strip()
    
    if not document_text:
        raise ConfigurationError("Document text is empty after sanitization")
    if not prompt_description:
        raise ConfigurationError("Prompt is empty after sanitization")
    if not model_id:
        raise ConfigurationError("Model ID is empty after sanitization")
    
    logger.debug("Pre-call validation passed - calling LangExtract...")
    
    # Wrap LangExtract call with enhanced error handling
    try:
        result = lx.extract(
            text_or_documents=document_text,
            prompt_description=prompt_description,
            examples=examples,
            model_id=model_id
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

    # Enhanced result validation with detailed logging
    logger.debug("Validating LangExtract response...")
    
    if not result:
        raise ModelResponseError("LangExtract returned None/empty result")
    
    logger.debug(f"Result type: {type(result)}")
    logger.debug(f"Result attributes: {dir(result)}")
    
    if not hasattr(result, 'extractions'):
        raise ModelResponseError("LangExtract result missing 'extractions' attribute")
    
    if result.extractions is None:
        raise ModelResponseError("LangExtract extractions is None")
    
    logger.debug(f"Extractions type: {type(result.extractions)}")
    logger.debug(f"Extractions count: {len(result.extractions) if hasattr(result.extractions, '__len__') else 'unknown'}")
    
    # Validate that extractions is iterable
    try:
        extraction_list = list(result.extractions)
        logger.debug(f"Successfully converted extractions to list with {len(extraction_list)} items")
    except (TypeError, AttributeError) as e:
        raise ModelResponseError(f"LangExtract extractions is not iterable: {e}")
    
    # Check for empty response
    if len(extraction_list) == 0:
        logger.warning("LangExtract returned empty extractions list")
        # Don't raise error here, let the validation below handle it

    extractions = []
    for i, extraction in enumerate(result.extractions):
        logger.debug(f"Processing extraction {i}: type={type(extraction)}")
        
        try:
            # Validate extraction object structure
            if not hasattr(extraction, 'extraction_text'):
                logger.warning(f"Extraction {i} missing 'extraction_text' attribute")
                continue
            
            if not hasattr(extraction, 'extraction_class'):
                logger.warning(f"Extraction {i} missing 'extraction_class' attribute")
                continue
            
            extraction_text = extraction.extraction_text
            extraction_class = extraction.extraction_class
            
            logger.debug(f"Extraction {i}: class='{extraction_class}', text='{extraction_text[:50]}...'")
            
            # Filter out empty or invalid extractions
            if (extraction_text and
                    extraction_text.strip() and
                    extraction_text.lower() not in ['null', 'none', 'n/a', '', 'na'] and
                    len(extraction_text.strip()) > 2):  # Reduced from 5 to 2 for IDs
                
                attributes = getattr(extraction, 'attributes', {})
                
                extractions.append({
                    "extraction_class": extraction_class,
                    "extraction_text": extraction_text.strip(),
                    "attributes": attributes if attributes else {}
                })
                
                logger.debug(f"Added valid extraction {i}: {extraction_class}")
            else:
                logger.debug(f"Skipped invalid extraction {i}: '{extraction_text}' (too short or invalid)")
                
        except Exception as e:
            logger.warning(f"Error processing extraction {i}: {e}")
            continue

    logger.info(f"Processed {len(result.extractions)} raw extractions, kept {len(extractions)} valid ones")

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
    
    # Enhanced prompt validation
    prompt = config["prompt"]
    if not isinstance(prompt, str):
        raise ConfigurationError("prompt must be a string")
    
    if len(prompt.strip()) == 0:
        raise ConfigurationError("prompt cannot be empty or whitespace only")
    
    if len(prompt.strip()) < 20:
        raise ConfigurationError("prompt is too short - must be at least 20 characters for meaningful extraction")
    
    # Validate model_id
    model_id = config["model_id"]
    if not isinstance(model_id, str):
        raise ConfigurationError("model_id must be a string")
    
    if len(model_id.strip()) == 0:
        raise ConfigurationError("model_id cannot be empty or whitespace only")


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


def _create_intermediate_results(extractions: List[Dict[str, Any]], 
                               extraction_attempts: List[Dict[str, Any]], 
                               state: MultiAgentState, 
                               settings: Settings) -> Dict[str, Any]:
    """Create comprehensive intermediate results for debugging and monitoring."""
    import time
    from typing import Set
    
    logger = logging.getLogger(__name__)
    
    # Determine which methods were used and which were fallbacks
    methods_used = [attempt["method"] for attempt in extraction_attempts]
    successful_methods = [attempt["method"] for attempt in extraction_attempts if attempt["status"] == "success"]
    fallback_used = "mock" in successful_methods
    langextract_failed = any(attempt["method"] == "langextract" and attempt["status"] != "success" for attempt in extraction_attempts)
    
    # Analyze extracted entities
    entity_analysis = _analyze_extracted_entities(extractions)
    
    # Get config analysis
    config_analysis = _analyze_config_quality(state.get("config", {}))
    
    # Document processing analysis
    doc_analysis = _analyze_document_processing(state)
    
    # Fallback analysis
    fallback_analysis = _analyze_fallback_usage(extraction_attempts, langextract_failed, fallback_used)
    
    intermediate_results = {
        "timestamp": time.time(),
        "extraction_summary": {
            "total_extractions": len(extractions),
            "methods_attempted": len(set(methods_used)),
            "successful_methods": successful_methods,
            "fallback_used": fallback_used,
            "langextract_failed": langextract_failed
        },
        "extracted_entities": entity_analysis,
        "config_analysis": config_analysis,
        "document_analysis": doc_analysis,
        "fallback_analysis": fallback_analysis,
        "extraction_attempts_detailed": extraction_attempts,
        "processing_metadata": {
            "model_used": state.get("config", {}).get("model_id", "unknown"),
            "document_length": len(state.get("document_text", "")),
            "chunks_processed": len(state.get("chunks", [])),
            "progressive_results_count": len(state.get("progressive_results", [])),
            "settings_used": {
                "max_fields": getattr(settings.extraction, 'max_fields', 'unknown'),
                "model": getattr(settings.models, 'extraction_model', 'unknown')
            }
        }
    }
    
    logger.info(f"Created intermediate results with {len(extractions)} entities and fallback_used={fallback_used}")
    return intermediate_results


# HELPER FUNCTIONS

def _analyze_extracted_entities(extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the quality and types of extracted entities."""
    if not extractions:
        return {
            "entity_count": 0,
            "entity_types": [],
            "categories": {},
            "quality_metrics": {
                "avg_text_length": 0,
                "empty_extractions": 0,
                "has_attributes": 0
            }
        }
    
    # Analyze entity types and categories
    entity_types = [ext.get("extraction_class", "unknown") for ext in extractions]
    categories = {}
    
    text_lengths = []
    empty_count = 0
    with_attributes = 0
    
    for extraction in extractions:
        # Category analysis
        attributes = extraction.get("attributes", {})
        if attributes and "category" in attributes:
            category = attributes["category"]
            categories[category] = categories.get(category, 0) + 1
        
        # Quality metrics
        text = extraction.get("extraction_text", "")
        text_lengths.append(len(text))
        
        if not text or len(text.strip()) == 0:
            empty_count += 1
            
        if attributes:
            with_attributes += 1
    
    return {
        "entity_count": len(extractions),
        "entity_types": list(set(entity_types)),
        "entity_type_counts": {etype: entity_types.count(etype) for etype in set(entity_types)},
        "categories": categories,
        "quality_metrics": {
            "avg_text_length": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
            "empty_extractions": empty_count,
            "has_attributes": with_attributes,
            "completeness_rate": (len(extractions) - empty_count) / len(extractions) if len(extractions) > 0 else 0
        },
        "sample_extractions": extractions[:3]  # First 3 for review
    }


def _analyze_config_quality(config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality of the extraction configuration."""
    if not config:
        return {
            "config_available": False,
            "quality_score": 0,
            "issues": ["No config provided"]
        }
    
    issues = []
    quality_score = 0
    
    # Check prompt quality
    prompt = config.get("prompt", "")
    if not prompt:
        issues.append("Empty prompt")
    elif len(prompt) < 50:
        issues.append("Prompt too short")
        quality_score += 25
    else:
        quality_score += 50
    
    # Check examples
    examples = config.get("examples", [])
    if not examples:
        issues.append("No examples provided")
    else:
        quality_score += 25
    
    # Check model
    model_id = config.get("model_id", "")
    if model_id:
        quality_score += 25
    else:
        issues.append("No model specified")
    
    return {
        "config_available": True,
        "quality_score": quality_score,
        "issues": issues,
        "prompt_length": len(prompt),
        "examples_count": len(examples),
        "model_id": model_id,
        "extraction_classes": config.get("extraction_classes", [])
    }


def _analyze_document_processing(state: MultiAgentState) -> Dict[str, Any]:
    """Analyze document processing quality and completeness."""
    doc_text = state.get("document_text", "")
    chunks = state.get("chunks", [])
    progressive_results = state.get("progressive_results", [])
    
    return {
        "document_stats": {
            "text_length": len(doc_text),
            "text_preview": doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
            "chunks_count": len(chunks),
            "progressive_results_count": len(progressive_results)
        },
        "processing_completeness": {
            "has_text": bool(doc_text),
            "has_chunks": bool(chunks),
            "has_progressive_results": bool(progressive_results),
            "chunking_effective": len(chunks) > 0 if doc_text else False
        }
    }


def _analyze_fallback_usage(extraction_attempts: List[Dict[str, Any]], 
                          langextract_failed: bool, 
                          fallback_used: bool) -> Dict[str, Any]:
    """Analyze fallback usage and provide recommendations."""
    
    # Find LangExtract failure details
    langextract_errors = []
    for attempt in extraction_attempts:
        if attempt["method"] == "langextract" and attempt["status"] != "success":
            error_info = {
                "status": attempt["status"],
                "error": attempt.get("error", "Unknown error")
            }
            langextract_errors.append(error_info)
    
    # Determine fallback reasons
    fallback_reasons = []
    if langextract_failed:
        fallback_reasons.append("LangExtract method failed")
    if not any(attempt["method"] == "langextract" for attempt in extraction_attempts):
        fallback_reasons.append("LangExtract not available")
    
    # Recommendations
    recommendations = []
    if fallback_used:
        recommendations.append("Consider investigating LangExtract failures for better extraction quality")
        if langextract_errors:
            error_types = [err["status"] for err in langextract_errors]
            if "json_error" in error_types:
                recommendations.append("Model is returning malformed JSON - consider prompt engineering")
            if "model_error" in error_types:
                recommendations.append("Model API issues detected - check quotas and connectivity")
    
    return {
        "fallback_used": fallback_used,
        "langextract_failed": langextract_failed,
        "fallback_reasons": fallback_reasons,
        "langextract_errors": langextract_errors,
        "impact_assessment": {
            "quality_impact": "medium" if fallback_used else "none",
            "reliability_impact": "low" if fallback_used else "none"
        },
        "recommendations": recommendations
    }
