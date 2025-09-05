"""
Schema discovery agent for analyzing documents and identifying extractable fields.
Uses Pydantic AI to analyze document structure and suggest extraction schemas.
"""

import os
from typing import List, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()

class FieldSchema(BaseModel):
    """Schema for a single extractable field."""
    field_name: str
    field_type: str 
    description: str
    example_text: str
    attributes: Dict[str, str]

class DocumentSchema(BaseModel):
    """Complete schema for document extraction."""
    document_type: str
    extraction_classes: List[FieldSchema]
    extraction_prompt: str

class SchemaDiscoveryDeps(BaseModel):
    """Dependencies for schema discovery agent."""
    document_text: str
    document_type: str = "unknown"

schema_discovery_agent = Agent(
    'gemini-2.0-flash',
    result_type=DocumentSchema,
    deps_type=SchemaDiscoveryDeps,
)

@schema_discovery_agent.system_prompt
def schema_discovery_prompt(ctx: RunContext[SchemaDiscoveryDeps]) -> str:
    """Generate prompt for schema discovery."""
    return f"""
Analyze this document and identify the key structured data that should be extracted.

Document to analyze:
{ctx.deps.document_text[:2000]}...

Create an extraction schema with:
1. Document type (e.g., "resume", "invoice", "contract") 
2. 3-5 most important extraction classes
3. For each class: name, type, description, example from text, and useful attributes
4. An overall extraction prompt

Focus on the most valuable structured information. Keep it simple and practical.
"""

class SchemaDiscovery:
    """Discovers extraction schemas from documents."""
    
    def __init__(self):
        """Initialize schema discovery agent."""
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    
    async def discover_schema(self, document_text: str, document_type: str = "unknown") -> DocumentSchema:
        """Discover extraction schema for a document."""
        try:
            deps = SchemaDiscoveryDeps(
                document_text=document_text,
                document_type=document_type
            )
            
            result = await schema_discovery_agent.run(
                "Analyze this document and create an extraction schema",
                deps=deps
            )
            
            return result.data
            
        except Exception as e:
            # Fallback schema for CV
            return DocumentSchema(
                document_type="resume",
                extraction_classes=[
                    FieldSchema(
                        field_name="personal_info",
                        field_type="contact",
                        description="Name, email, phone, location",
                        example_text="Hamza Khaled Mahmoud Ahmed",
                        attributes={"type": "identity"}
                    ),
                    FieldSchema(
                        field_name="skills",
                        field_type="technical_skill",
                        description="Technical skills and technologies",
                        example_text="Python, Machine Learning, TensorFlow",
                        attributes={"category": "technical"}
                    )
                ],
                extraction_prompt="Extract personal information and technical skills from this resume."
            )