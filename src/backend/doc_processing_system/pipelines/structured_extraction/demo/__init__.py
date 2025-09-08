"""
Multi-agent structured extraction demo.
Configurable, modular pipeline for document processing.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .config.settings import Settings
from .graph import build_graph, create_initial_state
from .models.state import MultiAgentState


async def run_extraction(
    document_text: str,
    document_id: str,
    settings: Optional[Settings] = None
) -> MultiAgentState:
    """
    Run multi-agent structured extraction workflow.
    
    Perfect entry point for Prefect flows.
    
    Args:
        document_text: Text content to extract from
        document_id: Unique identifier for the document
        settings: Configuration settings (uses defaults if None)
    
    Returns:
        MultiAgentState: Final workflow state with results
    """
    if settings is None:
        settings = Settings.create_default()
    
    # Build workflow graph
    workflow = build_graph(settings)
    
    # Create initial state
    initial_state = create_initial_state(document_text, document_id)
    
    # Execute workflow
    result = await workflow.ainvoke(initial_state)
    
    return result


def run_extraction_sync(
    document_text: str,
    document_id: str, 
    settings: Optional[Settings] = None
) -> MultiAgentState:
    """
    Synchronous wrapper for run_extraction.
    For use cases that require sync interface.
    """
    import asyncio
    return asyncio.run(run_extraction(document_text, document_id, settings))


def load_document(file_path: str) -> str:
    """Load document text from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def save_results(
    results: MultiAgentState,
    output_dir: str = "demo_results"
) -> Dict[str, str]:
    """
    Save extraction results to files.
    
    Returns:
        Dict with paths to saved files
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    document_id = results.get("document_id", "unknown")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save JSON results
    json_filename = f"{document_id}_{timestamp}_extraction.json"
    json_path = output_path / json_filename
    
    json_data = {
        "metadata": {
            "document_id": document_id,
            "extraction_timestamp": timestamp,
            "status": results.get("status", "unknown")
        },
        "final_schema": _serialize_schema(results.get("final_schema")),
        "extractions": results.get("extractions", []),
        **({"error": results["error"]} if results.get("error") else {})
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Save summary
    summary_filename = f"{document_id}_{timestamp}_summary.md"
    summary_path = output_path / summary_filename
    
    summary = _generate_summary(results)
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    return {
        "json_path": str(json_path),
        "summary_path": str(summary_path)
    }


def _serialize_schema(schema) -> Dict[str, Any]:
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


def _generate_summary(results: MultiAgentState) -> str:
    """Generate human-readable summary."""
    document_id = results.get("document_id", "Unknown Document")
    status = results.get("status", "unknown")
    extractions = results.get("extractions", [])
    
    summary = f"""# Structured Extraction Results

**Document**: {document_id}
**Status**: {status}
**Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Discovered Schema
"""
    
    schema = results.get("final_schema")
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


# Convenience exports
__all__ = [
    "run_extraction",
    "run_extraction_sync", 
    "load_document",
    "save_results",
    "Settings"
]