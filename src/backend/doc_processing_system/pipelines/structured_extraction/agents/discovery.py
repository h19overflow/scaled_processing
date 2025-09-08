"""
Sequential schema discovery agent.
"""

from typing import List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from ..models.schema import FieldSchema, ProgressiveSchema


class SequentialDiscoveryDeps(BaseModel):
    """Dependencies for sequential schema discovery."""
    chunk_text: str
    chunk_id: int
    previous_discoveries: List[FieldSchema]
    document_type: str


def create_discovery_agent(model_name: str) -> Agent:
    """Create a discovery agent with specified model."""

    agent = Agent(
        model_name,
        result_type=ProgressiveSchema,
        deps_type=SequentialDiscoveryDeps,
    )

    @agent.system_prompt
    def discovery_prompt(ctx: RunContext[SequentialDiscoveryDeps]) -> str:
        """Generate prompt for sequential schema discovery."""

        previous_fields = "None yet" if not ctx.deps.previous_discoveries else "\n".join([
            f"- {field.field_name}: {field.description}"
            for field in ctx.deps.previous_discoveries
        ])

        return f"""
You are analyzing chunk #{ctx.deps.chunk_id} of a {ctx.deps.document_type} document.

PREVIOUS DISCOVERIES from earlier chunks:
{previous_fields}

CURRENT CHUNK TO ANALYZE:
{ctx.deps.chunk_text}

Your task:
1. Identify NEW extractable fields that weren't captured in previous discoveries
2. Look for different types of information that appear in this part of the document
3. Focus on fields that would be valuable for structured extraction
4. Avoid duplicating already discovered fields unless you find a significantly different aspect

Create a progressive schema with:
- discovered_fields: NEW fields found in this chunk (3-5 max)
- document_type: Confirm or refine document type
- confidence_level: "high", "medium", or "low" based on clarity of fields
- chunk_coverage: How much of document has been processed (chunk_id + 1)

Focus on practical, extractable information. Be specific about field types and attributes.
"""

    return agent
