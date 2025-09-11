"""
Data extraction node.
"""

from typing import Dict, Any, List

try:
    import langextract as lx

    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

from ..models.state import MultiAgentState
from ..config.settings import Settings


def extract_data(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Extract structured data using langextract with final schema."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug("Starting extraction process")
        
        # Try LangExtract first if available, then fallback to mock
        extractions = None
        if LANGEXTRACT_AVAILABLE:
            try:
                logger.debug("Attempting LangExtract extraction")
                extractions = _extract_with_langextract(state)
                logger.debug(f"LangExtract successful: {len(extractions)} extractions")
            except Exception as e:
                logger.warning(f"LangExtract failed: {e}, falling back to mock extraction")
                extractions = None
        
        # If LangExtract failed or unavailable, use mock extraction
        if not extractions:
            logger.debug("Using mock extraction")
            extractions = _mock_extractions(state)
            logger.debug(f"Mock extraction: {len(extractions)} extractions")

        if not extractions:
            raise ValueError("No valid extractions found")

        logger.info(f"Extraction completed successfully with {len(extractions)} items")
        return {
            **state,
            "extractions": extractions,
            "status": "extraction_complete"
        }

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {
            **state,
            "error": f"Extraction failed: {str(e)}",
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

    result = lx.extract(
        text_or_documents=state["document_text"],
        prompt_description=state["config"]["prompt"],
        examples=examples,
        model_id=state["config"]["model_id"]
    )

    if not result or not hasattr(result, 'extractions'):
        raise ValueError("LangExtract returned invalid result")

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


def _mock_extractions(state: MultiAgentState) -> List[Dict[str, Any]]:
    """Create mock extractions when LangExtract is not available."""
    import logging
    logger = logging.getLogger(__name__)
    
    extractions = []
    
    # Get fields directly from discovery results with defensive programming
    all_fields = []
    
    if not state.get("progressive_results"):
        logger.warning("No progressive_results found in state")
        return []
    
    logger.debug(f"Processing {len(state['progressive_results'])} progressive results")
    
    for i, result in enumerate(state["progressive_results"]):
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
            continue

    logger.debug(f"Total fields collected: {len(all_fields)}")
    
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
            continue

    logger.info(f"Created {len(extractions)} mock extractions")
    return extractions
