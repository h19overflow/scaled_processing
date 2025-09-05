"""
Sequential schema discovery agent for multi-batch document processing.
Progressively discovers schemas while being aware of previous findings.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .models import FieldSchema, DocumentSchema
from .document_chunker import DocumentChunk
from .logging_config import log_agent_call, log_schema_discovery

load_dotenv()

class ProgressiveSchema(BaseModel):
    """Schema that builds progressively across chunks."""
    discovered_fields: List[FieldSchema]
    document_type: str
    confidence_level: str
    chunk_coverage: int

class SequentialDiscoveryDeps(BaseModel):
    """Dependencies for sequential schema discovery."""
    chunk_text: str
    chunk_id: int
    previous_discoveries: List[FieldSchema]
    document_type: str

sequential_discovery_agent = Agent(
    'gemini-2.0-flash',
    result_type=ProgressiveSchema,
    deps_type=SequentialDiscoveryDeps,
)

@sequential_discovery_agent.system_prompt
def sequential_discovery_prompt(ctx: RunContext[SequentialDiscoveryDeps]) -> str:
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

class SequentialSchemaDiscovery:
    """Discovers schemas progressively across document chunks."""
    
    def __init__(self):
        """Initialize sequential schema discovery."""
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.discovered_fields: List[FieldSchema] = []
        self.document_type: str = "unknown"
        self.logger = logging.getLogger("multi_agent_extraction")
    
    async def discover_chunk_schema(
        self, 
        chunk: DocumentChunk, 
        document_type: str = "unknown"
    ) -> ProgressiveSchema:
        """Discover schema for a single chunk considering previous discoveries."""
        self.logger.debug(f"Processing chunk {chunk.chunk_id}: {len(chunk.text)} chars, {chunk.token_count} tokens")
        
        try:
            # Log input preparation
            input_data = {
                "chunk_id": chunk.chunk_id,
                "chunk_length": len(chunk.text),
                "previous_fields_count": len(self.discovered_fields),
                "document_type": self.document_type if self.document_type != "unknown" else document_type
            }
            log_agent_call(self.logger, "SequentialDiscovery", input_data, "start")
            
            deps = SequentialDiscoveryDeps(
                chunk_text=chunk.text,
                chunk_id=chunk.chunk_id,
                previous_discoveries=self.discovered_fields.copy(),
                document_type=self.document_type if self.document_type != "unknown" else document_type
            )
            
            self.logger.debug(f"Sending to agent: {len(deps.chunk_text)} chars, {len(deps.previous_discoveries)} previous fields")
            
            result = await sequential_discovery_agent.run(
                f"Analyze chunk {chunk.chunk_id} and find new extractable fields",
                deps=deps
            )
            
            # Update accumulated discoveries
            progressive_schema = result.data
            new_fields_count = len(progressive_schema.discovered_fields)
            
            self.discovered_fields.extend(progressive_schema.discovered_fields)
            self.document_type = progressive_schema.document_type
            
            log_schema_discovery(self.logger, chunk.chunk_id, new_fields_count, len(self.discovered_fields))
            log_agent_call(self.logger, "SequentialDiscovery", {"fields_discovered": new_fields_count}, "success")
            
            return progressive_schema
            
        except Exception as e:
            self.logger.error(f"Schema discovery error for chunk {chunk.chunk_id}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            log_agent_call(self.logger, "SequentialDiscovery", {"error": str(e)}, "error")
            
            # Fallback progressive schema with basic fields
            basic_fields = [
                FieldSchema(
                    field_name="personal_info",
                    field_type="contact",
                    description="Name, email, phone, location",
                    example_text="Personal contact information",
                    category="identity",
                    subcategory="contact"
                ),
                FieldSchema(
                    field_name="skills",
                    field_type="technical_skill", 
                    description="Technical skills and technologies",
                    example_text="Programming languages and tools",
                    category="technical",
                    subcategory="programming"
                )
            ]
            
            fallback_schema = ProgressiveSchema(
                discovered_fields=basic_fields if chunk.chunk_id == 0 else [],
                document_type="resume" if document_type == "unknown" else document_type,
                confidence_level="low",
                chunk_coverage=chunk.chunk_id + 1
            )
            
            # Update accumulated discoveries even with fallback
            if chunk.chunk_id == 0:
                self.discovered_fields.extend(basic_fields)
                self.document_type = fallback_schema.document_type
            
            self.logger.warning(f"Using fallback schema for chunk {chunk.chunk_id}: {len(fallback_schema.discovered_fields)} basic fields")
            
            return fallback_schema
    
    async def process_all_chunks(
        self, 
        chunks: List[DocumentChunk], 
        document_type: str = "unknown"
    ) -> List[ProgressiveSchema]:
        """Process all chunks sequentially and build progressive schema."""
        progressive_results = []
        
        for chunk in chunks:
            print(f"🔍 Processing chunk {chunk.chunk_id}/{len(chunks)-1} ({chunk.token_count} tokens)")
            
            progressive_schema = await self.discover_chunk_schema(chunk, document_type)
            progressive_results.append(progressive_schema)
            
            # Show progress
            new_fields = len(progressive_schema.discovered_fields)
            total_fields = len(self.discovered_fields)
            print(f"  📊 Found {new_fields} new fields, total: {total_fields}")
        
        return progressive_results
    
    def get_consolidated_schema(self, extraction_prompt: Optional[str] = None) -> DocumentSchema:
        """Get final consolidated schema from all discoveries."""
        if not extraction_prompt:
            field_descriptions = [f"{field.field_name}: {field.description}" 
                                for field in self.discovered_fields]
            extraction_prompt = f"Extract structured data from this {self.document_type} including: {', '.join(field_descriptions[:5])}"
        
        return DocumentSchema(
            document_type=self.document_type,
            extraction_classes=self.discovered_fields,
            extraction_prompt=extraction_prompt
        )
    
    def reset(self):
        """Reset discovered fields for new document."""
        self.discovered_fields = []
        self.document_type = "unknown"