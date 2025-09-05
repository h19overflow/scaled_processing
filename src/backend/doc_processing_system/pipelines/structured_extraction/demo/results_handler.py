"""
Results handler for structured extraction demo.
Saves extraction results and generates summary reports.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class ResultsHandler:
    """Handles saving and formatting extraction results."""
    
    def __init__(self, output_dir: str = None):
        """Initialize results handler."""
        if output_dir is None:
            output_dir = "src/backend/doc_processing_system/pipelines/structured_extraction/demo_results"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_results(self, results: Dict[str, Any]) -> str:
        """Save extraction results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = results.get("document_id", "unknown")
        
        # Create results with metadata
        output_data = {
            "metadata": {
                "document_id": document_id,
                "extraction_timestamp": timestamp,
                "status": results.get("status", "unknown"),
                "langextract_demo": True
            },
            "schema": self._serialize_schema(results.get("schema")),
            "config": self._serialize_config(results.get("config", {})),
            "extractions": results.get("extractions", []),
            # Only include error field if there's an actual error
            **({"error": results["error"]} if results.get("error") else {})
        }
        
        # Save to file
        filename = f"{document_id}_{timestamp}_extraction.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate human-readable summary of extraction results."""
        document_id = results.get("document_id", "Unknown Document")
        status = results.get("status", "unknown")
        extractions = results.get("extractions", [])
        
        summary = f"""
# Structured Extraction Results

**Document**: {document_id}
**Status**: {status}
**Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Discovered Schema
"""
        
        schema = results.get("schema")
        if schema:
            summary += f"**Document Type**: {schema.document_type}\n\n"
            summary += "**Extraction Classes**:\n"
            for field in schema.extraction_classes:
                summary += f"- **{field.field_name}**: {field.description}\n"
        
        summary += f"\n## Extraction Results ({len(extractions)} items)\n\n"
        
        for i, extraction in enumerate(extractions, 1):
            summary += f"### {i}. {extraction['extraction_class']}\n"
            summary += f"**Text**: {extraction['extraction_text']}\n"
            summary += f"**Attributes**: {extraction['attributes']}\n\n"
        
        if results.get("error"):
            summary += f"\n## Error\n{results['error']}\n"
        
        return summary
    
    def save_summary(self, results: Dict[str, Any]) -> str:
        """Save summary report to markdown file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = results.get("document_id", "unknown")
        
        summary = self.generate_summary(results)
        
        filename = f"{document_id}_{timestamp}_summary.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return str(filepath)
    
    def _serialize_schema(self, schema) -> Dict[str, Any]:
        """Convert schema object to serializable dict."""
        if not schema:
            return {}
        
        return {
            "document_type": schema.document_type,
            "extraction_prompt": schema.extraction_prompt,
            "extraction_classes": [
                {
                    "field_name": field.field_name,
                    "field_type": field.field_type,
                    "description": field.description,
                    "example_text": field.example_text,
                    "category": field.category,
                    "subcategory": field.subcategory
                }
                for field in schema.extraction_classes
            ]
        }
    
    def _serialize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert config with examples to serializable format."""
        if not config:
            return {}
        
        serialized = config.copy()
        
        # Convert examples to serializable format
        if "examples" in serialized:
            examples = []
            for example in serialized["examples"]:
                example_dict = {
                    "text": example.text,
                    "extractions": [
                        {
                            "extraction_class": ext.extraction_class,
                            "extraction_text": ext.extraction_text,
                            "attributes": ext.attributes
                        }
                        for ext in example.extractions
                    ]
                }
                examples.append(example_dict)
            serialized["examples"] = examples
        
        return serialized