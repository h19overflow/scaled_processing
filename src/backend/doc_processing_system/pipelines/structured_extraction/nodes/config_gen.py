"""
Configuration generation node.
"""

from typing import List, Dict, Any
import textwrap

try:
    import langextract as lx

    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False


    class Extraction:
        def __init__(self, extraction_class: str, extraction_text: str, attributes: Dict[str, Any]):
            self.extraction_class = extraction_class
            self.extraction_text = extraction_text
            self.attributes = attributes


    class ExampleData:
        def __init__(self, text: str, extractions: List[Extraction]):
            self.text = text
            self.extractions = extractions

from ..models.state import MultiAgentState
from ..models.schema import FieldSchema
from ..config.settings import Settings


def generate_config(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Generate langextract configuration directly from discovery results."""
    try:
        # Get all discovered fields from progressive results
        all_fields = []
        for result in state["progressive_results"]:
            all_fields.extend(result.discovered_fields)
        
        if not all_fields:
            raise ValueError("No fields discovered to generate config")
        
        # Limit to max fields and remove duplicates
        seen_names = set()
        unique_fields = []
        for field in all_fields:
            if field.field_name.lower() not in seen_names:
                seen_names.add(field.field_name.lower())
                unique_fields.append(field)
                
                if len(unique_fields) >= settings.extraction.max_fields:
                    break
        
        sample_text = state["document_text"][:1000]
        config = _create_config_from_fields(unique_fields, sample_text, settings.models.extraction_model)

        return {
            **state,
            "config": config,
            "status": "config_generated"
        }

    except Exception as e:
        return {
            **state,
            "error": f"Config generation failed: {str(e)}",
            "status": "error"
        }


def _create_config_from_fields(fields: List[FieldSchema], sample_text: str, model_id: str) -> Dict[str, Any]:
    """Create langextract configuration directly from discovered fields."""

    # Create extraction prompt
    prompt = textwrap.dedent(f"""
        Extract structured information from this document.
        
        Extract the following types of information:
        {_format_field_list(fields)}
        
        IMPORTANT RULES:
        - Use exact text from the document for extractions
        - Only extract information that actually exists in the document
        - If information is not found, skip that extraction class
        - Provide meaningful attributes for context
        - Do not create empty or duplicate extractions
    """).strip()

    # Create example data
    examples = _create_examples(fields, sample_text)

    return {
        "prompt": prompt,
        "examples": examples,
        "model_id": model_id,
        "extraction_classes": [field.field_name for field in fields]
    }


def _create_config(schema, sample_text: str, model_id: str) -> Dict[str, Any]:
    """Create langextract configuration from schema."""

    # Create extraction prompt
    prompt = textwrap.dedent(f"""
        {schema.extraction_prompt}
        
        Extract the following types of information:
        {_format_extraction_classes(schema.extraction_classes)}
        
        IMPORTANT RULES:
        - Use exact text from the document for extractions
        - Only extract information that actually exists in the document
        - If information is not found, skip that extraction class
        - Provide meaningful attributes for context
        - Do not create empty or duplicate extractions
    """).strip()

    # Create example data
    examples = _create_examples(schema.extraction_classes, sample_text)

    return {
        "prompt": prompt,
        "examples": examples,
        "model_id": model_id,
        "extraction_classes": [field.field_name for field in schema.extraction_classes]
    }


def _format_field_list(fields: List[FieldSchema]) -> str:
    """Format field list for prompt."""
    formatted = []
    for field in fields:
        formatted.append(f"- {field.field_name}: {field.description}")
    return "\n".join(formatted)


def _format_extraction_classes(classes: List[FieldSchema]) -> str:
    """Format extraction classes for prompt."""
    formatted = []
    for field in classes:
        formatted.append(f"- {field.field_name}: {field.description}")
    return "\n".join(formatted)


def _create_examples(extraction_classes: List[FieldSchema], sample_text: str) -> List:
    """Create example extractions using document text."""
    if not sample_text:
        sample_text = "Sample document text for demonstration."

    # Create one extraction per class
    extractions = []
    for field in extraction_classes:
        example_text = field.example_text if field.example_text else f"Sample {field.field_name}"
        attributes = {"category": field.category, "subcategory": field.subcategory}

        if LANGEXTRACT_AVAILABLE:
            extraction = lx.data.Extraction(
                extraction_class=field.field_name,
                extraction_text=example_text,
                attributes=attributes
            )
        else:
            extraction = Extraction(
                extraction_class=field.field_name,
                extraction_text=example_text,
                attributes=attributes
            )
        extractions.append(extraction)

    # Use longer sample text for better alignment
    example_text = sample_text[:1500] if len(sample_text) > 1500 else sample_text

    # Create example data
    if LANGEXTRACT_AVAILABLE:
        example = lx.data.ExampleData(
            text=example_text,
            extractions=extractions
        )
    else:
        example = ExampleData(
            text=example_text,
            extractions=extractions
        )

    return [example]
