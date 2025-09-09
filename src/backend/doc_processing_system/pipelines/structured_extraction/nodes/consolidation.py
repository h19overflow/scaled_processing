"""
Schema consolidation node.
"""

import os
from typing import List

from ..models.state import MultiAgentState
from ..models.schema import FieldSchema, ConsolidatedSchema
from ..models.document import DocumentSchema
from ..config.settings import Settings
from ..agents.consolidation import create_consolidation_agent, ConsolidationDeps


async def consolidate_schema(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Consolidate discovered schemas into final optimized schema."""
    try:

        # Collect all discovered fields
        all_fields = []
        document_type = settings.extraction.document_type

        for result in state["progressive_results"]:
            all_fields.extend(result.discovered_fields)
            if result.document_type != "unknown":
                document_type = result.document_type

        if not all_fields:
            raise ValueError("No fields discovered to consolidate")

        # Create consolidation agent
        agent = create_consolidation_agent(settings.models.consolidation_model)

        deps = ConsolidationDeps(
            discovered_fields=all_fields,
            document_type=document_type,
            max_fields=settings.extraction.max_fields
        )

        result = await agent.run(
            f"Consolidate {len(all_fields)} discovered fields into optimized schema",
            deps=deps
        )

        consolidated = result.data
        final_schema = _to_document_schema(consolidated)

        if not final_schema.extraction_classes:
            raise ValueError("Schema consolidation produced no extraction classes")

        return {
            **state,
            "consolidated_schema": consolidated,
            "final_schema": final_schema,
            "status": "consolidated"
        }

    except Exception as e:
        # Fallback consolidation
        consolidated = _simple_consolidation(
            _get_all_fields(state["progressive_results"]),
            settings.extraction.document_type,
            settings.extraction.max_fields
        )
        final_schema = _to_document_schema(consolidated)

        return {
            **state,
            "consolidated_schema": consolidated,
            "final_schema": final_schema,
            "error": f"Schema consolidation failed: {str(e)}",
            "status": "consolidated"
        }


def _get_all_fields(progressive_results) -> List[FieldSchema]:
    """Extract all discovered fields from progressive results."""
    all_fields = []
    for result in progressive_results:
        all_fields.extend(result.discovered_fields)
    return all_fields


def _to_document_schema(consolidated: ConsolidatedSchema) -> DocumentSchema:
    """Convert consolidated schema to DocumentSchema format."""
    return DocumentSchema(
        document_type=consolidated.document_type,
        extraction_classes=consolidated.final_fields,
        extraction_prompt=consolidated.extraction_prompt
    )


def _simple_consolidation(
        fields: List[FieldSchema],
        document_type: str,
        max_fields: int
) -> ConsolidatedSchema:
    """Simple fallback consolidation when AI fails."""
    seen_names = set()
    unique_fields = []

    for field in fields:
        if field.field_name.lower() not in seen_names:
            seen_names.add(field.field_name.lower())
            unique_fields.append(field)

            if len(unique_fields) >= max_fields:
                break

    return ConsolidatedSchema(
        final_fields=unique_fields,
        document_type=document_type,
        optimization_notes="Fallback consolidation: basic deduplication applied",
        extraction_prompt=f"Extract structured information from this {document_type} document"
    )
