"""
Schema consolidation agent for merging and refining discovered schemas.
Removes duplicates, merges similar fields, and creates optimized final schema.
"""

import os
from typing import List, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .schema_discovery import FieldSchema, DocumentSchema

load_dotenv()

class ConsolidatedSchema(BaseModel):
    """Final consolidated schema after merging and optimization."""
    final_fields: List[FieldSchema]
    document_type: str
    optimization_notes: str
    extraction_prompt: str

class ConsolidationDeps(BaseModel):
    """Dependencies for schema consolidation."""
    discovered_fields: List[FieldSchema]
    document_type: str
    max_fields: int = 8

consolidation_agent = Agent(
    'gemini-2.0-flash-exp',
    result_type=ConsolidatedSchema,
    deps_type=ConsolidationDeps,
)

@consolidation_agent.system_prompt
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

class SchemaConsolidation:
    """Consolidates and optimizes discovered schemas."""
    
    def __init__(self):
        """Initialize schema consolidation."""
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    
    async def consolidate_schema(
        self, 
        discovered_fields: List[FieldSchema], 
        document_type: str,
        max_fields: int = 8
    ) -> ConsolidatedSchema:
        """Consolidate discovered fields into optimized final schema."""
        try:
            deps = ConsolidationDeps(
                discovered_fields=discovered_fields,
                document_type=document_type,
                max_fields=max_fields
            )
            
            result = await consolidation_agent.run(
                f"Consolidate {len(discovered_fields)} discovered fields into optimized schema",
                deps=deps
            )
            
            return result.data
            
        except Exception as e:
            # Fallback consolidation - simple deduplication
            return self._simple_consolidation(discovered_fields, document_type, max_fields)
    
    def to_document_schema(self, consolidated: ConsolidatedSchema) -> DocumentSchema:
        """Convert consolidated schema to DocumentSchema format."""
        return DocumentSchema(
            document_type=consolidated.document_type,
            extraction_classes=consolidated.final_fields,
            extraction_prompt=consolidated.extraction_prompt
        )
    
    # HELPER FUNCTIONS
    
    def _simple_consolidation(
        self, 
        fields: List[FieldSchema], 
        document_type: str, 
        max_fields: int
    ) -> ConsolidatedSchema:
        """Simple fallback consolidation when AI fails."""
        
        # Basic deduplication by field name
        seen_names = set()
        unique_fields = []
        
        for field in fields:
            if field.field_name.lower() not in seen_names:
                seen_names.add(field.field_name.lower())
                unique_fields.append(field)
                
                if len(unique_fields) >= max_fields:
                    break
        
        # Create fallback schema
        return ConsolidatedSchema(
            final_fields=unique_fields,
            document_type=document_type,
            optimization_notes="Fallback consolidation: basic deduplication applied",
            extraction_prompt=f"Extract structured information from this {document_type} document"
        )