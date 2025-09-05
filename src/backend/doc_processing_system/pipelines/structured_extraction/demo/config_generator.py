"""
Configuration generator for langextract.
Converts discovered schemas into langextract format with examples.
"""

import textwrap
from typing import List, Dict, Any
from .schema_discovery import DocumentSchema, FieldSchema

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    # Mock classes for when langextract isn't available
    class Extraction:
        def __init__(self, extraction_class: str, extraction_text: str, attributes: Dict[str, Any]):
            self.extraction_class = extraction_class
            self.extraction_text = extraction_text
            self.attributes = attributes
    
    class ExampleData:
        def __init__(self, text: str, extractions: List[Extraction]):
            self.text = text
            self.extractions = extractions

class ConfigGenerator:
    """Generates langextract configuration from discovered schemas."""
    
    def __init__(self):
        """Initialize config generator."""
        pass
    
    def generate_config(self, schema: DocumentSchema, sample_text: str = None) -> Dict[str, Any]:
        """Generate langextract configuration from schema."""
        
        # Create extraction prompt
        prompt = textwrap.dedent(f"""
            {schema.extraction_prompt}
            
            Extract the following types of information:
            {self._format_extraction_classes(schema.extraction_classes)}
            
            Use exact text for extractions. Provide meaningful attributes for context.
        """).strip()
        
        # Create example data
        examples = self._create_examples(schema, sample_text)
        
        return {
            "prompt": prompt,
            "examples": examples,
            "model_id": "gemini-2.5-flash",
            "extraction_classes": [field.field_name for field in schema.extraction_classes]
        }
    
    def _format_extraction_classes(self, classes: List[FieldSchema]) -> str:
        """Format extraction classes for prompt."""
        formatted = []
        for field in classes:
            formatted.append(f"- {field.field_name}: {field.description}")
        return "\n".join(formatted)
    
    def _create_examples(self, schema: DocumentSchema, sample_text: str = None) -> List:
        """Create example extractions for langextract."""
        if not sample_text:
            sample_text = "Sample document text for demonstration."
        
        # Create mock extractions based on schema
        extractions = []
        for field in schema.extraction_classes[:2]:  # Limit to 2 examples
            attributes = {"category": field.category, "subcategory": field.subcategory}
            if LANGEXTRACT_AVAILABLE:
                extraction = lx.data.Extraction(
                    extraction_class=field.field_name,
                    extraction_text=field.example_text,
                    attributes=attributes
                )
            else:
                extraction = Extraction(
                    extraction_class=field.field_name,
                    extraction_text=field.example_text,
                    attributes=attributes
                )
            extractions.append(extraction)
        
        # Create example data
        if LANGEXTRACT_AVAILABLE:
            example = lx.data.ExampleData(
                text=sample_text[:200],
                extractions=extractions
            )
        else:
            example = ExampleData(
                text=sample_text[:200],
                extractions=extractions
            )
        
        return [example]