"""
Schema consolidation agent.
"""

from typing import List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from ..models.schema import FieldSchema, ConsolidatedSchema


class ConsolidationDeps(BaseModel):
    """Dependencies for schema consolidation."""
    discovered_fields: List[FieldSchema]
    document_type: str
    max_fields: int = 8


def create_consolidation_agent(model_name: str) -> Agent:
    """Create a consolidation agent with specified model."""

    agent = Agent(
        model_name,
        result_type=ConsolidatedSchema,
        deps_type=ConsolidationDeps,
    )

    @agent.system_prompt
    def consolidation_prompt(ctx: RunContext[ConsolidationDeps]) -> str:
        """Generate prompt for schema consolidation."""

        fields_text = "\n".join([
            f"- {field.field_name} ({field.field_type}): {field.description}"
            for field in ctx.deps.discovered_fields
        ])

        return f"""
You have discovered {len(ctx.deps.discovered_fields)} fields from a {ctx.deps.document_type} document.

DISCOVERED FIELDS:
{fields_text}

Your task is to consolidate these into a clean, optimized schema:

1. REMOVE DUPLICATES: Merge similar/duplicate fields into single comprehensive fields
2. PRIORITIZE VALUE: Keep the {ctx.deps.max_fields} most valuable extractable fields
3. OPTIMIZE DESCRIPTIONS: Make field descriptions clear and specific
4. MERGE RELATED: Combine related fields (e.g., "name", "full_name" -> "personal_name")
5. IMPROVE ATTRIBUTES: Enhance attribute definitions for better extraction

Create a consolidated schema with:
- final_fields: {ctx.deps.max_fields} or fewer optimized fields
- document_type: Refined document type
- optimization_notes: Brief explanation of changes made
- extraction_prompt: Clear, comprehensive extraction prompt

Focus on fields that will provide the most value for structured data extraction.
Each field should be distinct, well-defined, and practically extractable.
"""

    return agent
