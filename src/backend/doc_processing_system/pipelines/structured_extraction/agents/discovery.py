"""
Sequential schema discovery agent.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from ..models.schema import FieldSchema, ProgressiveSchema


class SequentialDiscoveryDeps(BaseModel):
    """Dependencies for sequential schema discovery."""
    chunk_text: str
    chunk_id: int
    previous_discoveries: List[FieldSchema]
    document_type: str
    user_preferences: Dict[str, Any]
    feedback_context: Dict[str, Any]
    user_id: str
    classification: str


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

        # Build user preferences context
        preferences_context = _build_preferences_context(ctx.deps.user_preferences)
        
        # Build feedback context
        feedback_context = _build_feedback_context(ctx.deps.feedback_context)

        return f"""
You are analyzing chunk #{ctx.deps.chunk_id} of a {ctx.deps.document_type} document for user {ctx.deps.user_id}.

PREVIOUS DISCOVERIES from earlier chunks:
{previous_fields}

{preferences_context}

{feedback_context}

CURRENT CHUNK TO ANALYZE:
{ctx.deps.chunk_text}

Your task:
1. Identify NEW extractable fields that weren't captured in previous discoveries
2. Look for different types of information that appear in this part of the document
3. Focus on fields that would be valuable for structured extraction
4. Consider user preferences and feedback when determining field importance
5. Avoid duplicating already discovered fields unless you find a significantly different aspect
6. Pay special attention to fields mentioned in user preferences or feedback

Create a progressive schema with:
- discovered_fields: NEW fields found in this chunk (3-5 max, prioritize based on user preferences)
- document_type: Confirm or refine document type (classification: {ctx.deps.classification})
- confidence_level: "high", "medium", or "low" based on clarity of fields
- chunk_coverage: How much of document has been processed (chunk_id + 1)

Focus on practical, extractable information that aligns with user preferences and feedback. Be specific about field types and attributes.
"""

    return agent


# HELPER FUNCTIONS

def _build_preferences_context(user_preferences: Dict[str, Any]) -> str:
    """Build context string from user preferences."""
    if not user_preferences:
        return "USER PREFERENCES: No specific preferences available."
    
    context_parts = ["USER PREFERENCES:"]
    
    # Add prompt instructions
    prompt_instructions = user_preferences.get("prompt_instructions", "")
    if prompt_instructions:
        context_parts.append(f"Special instructions: {prompt_instructions}")
    
    # Add field preferences
    field_preferences = user_preferences.get("field_preferences", {})
    if field_preferences:
        field_priorities = field_preferences.get("field_priorities", {})
        if field_priorities:
            high_priority_fields = [
                field for field, settings in field_priorities.items()
                if settings.get("weight", 0) >= 0.8
            ]
            if high_priority_fields:
                context_parts.append(f"High priority fields: {', '.join(high_priority_fields)}")
        
        field_mappings = field_preferences.get("field_mappings", {})
        if field_mappings:
            context_parts.append(f"Field mappings: {field_mappings}")
    
    # Add extraction style preferences
    extraction_style = user_preferences.get("extraction_style", {})
    if extraction_style:
        style_parts = []
        
        verbosity = extraction_style.get("verbosity", "standard")
        if verbosity != "standard":
            style_parts.append(f"verbosity: {verbosity}")
        
        confidence_threshold = extraction_style.get("confidence_threshold")
        if confidence_threshold:
            style_parts.append(f"minimum confidence: {confidence_threshold}")
        
        if style_parts:
            context_parts.append(f"Extraction style: {', '.join(style_parts)}")
    
    return "\n".join(context_parts)


def _build_feedback_context(feedback_context: Dict[str, Any]) -> str:
    """Build context string from user feedback."""
    if not feedback_context or not feedback_context.get("relevant_feedback"):
        return "FEEDBACK CONTEXT: No relevant feedback available."
    
    context_parts = ["FEEDBACK CONTEXT:"]
    
    # Add context prompt if available
    context_prompt = feedback_context.get("context_prompt", "")
    if context_prompt:
        context_parts.append(context_prompt)
    
    # Add field corrections
    field_corrections = feedback_context.get("field_corrections", {})
    if field_corrections:
        context_parts.append("Field-specific corrections from previous feedback:")
        for field_name, corrections in field_corrections.items():
            unique_corrections = list(set(corrections))
            if unique_corrections:
                context_parts.append(f"- {field_name}: {', '.join(unique_corrections[:2])}")
    
    # Add common issues
    common_issues = feedback_context.get("common_issues", [])
    if common_issues:
        context_parts.append("Common issues to avoid:")
        for issue in common_issues[:2]:
            context_parts.append(f"- {issue}")
    
    return "\n".join(context_parts)
