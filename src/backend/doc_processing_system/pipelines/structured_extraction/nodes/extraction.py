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
    try:
        if LANGEXTRACT_AVAILABLE:
            extractions = _extract_with_langextract(state)
        else:
            extractions = _mock_extractions(state)

        if not extractions:
            raise ValueError("No valid extractions found")

        return {
            **state,
            "extractions": extractions,
            "status": "extraction_complete"
        }

    except Exception as e:
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

    result = lx.extract(
        text_or_documents=state["document_text"],
        prompt_description=state["config"]["prompt"],
        examples=state["config"]["examples"],
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
    extractions = []
    
    # Get fields directly from discovery results
    all_fields = []
    for result in state["progressive_results"]:
        all_fields.extend(result.discovered_fields)

    for field in all_fields[:3]:  # Limit to first 3 for mock
        extractions.append({
            "extraction_class": field.field_name,
            "extraction_text": field.sample_values[0] if field.sample_values else f"Sample {field.field_name}",
            "attributes": {"category": field.category, "subcategory": field.subcategory}
        })

    return extractions
