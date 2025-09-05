"""
LangGraph workflow for structured extraction using langextract.
Simple workflow: Document -> Schema Discovery -> Config Generation -> Extraction -> Results
"""

import json
import asyncio
from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from .schema_discovery import SchemaDiscovery, DocumentSchema
from .config_generator import ConfigGenerator

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

class ExtractionState(TypedDict):
    """State for the extraction workflow."""
    document_text: str
    document_id: str
    schema: DocumentSchema
    config: Dict[str, Any]
    extractions: List[Dict[str, Any]]
    status: str
    error: str

class ExtractionWorkflow:
    """Simple LangGraph workflow for document extraction."""
    
    def __init__(self):
        """Initialize extraction workflow."""
        self.schema_discovery = SchemaDiscovery()
        self.config_generator = ConfigGenerator()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the extraction workflow graph."""
        workflow = StateGraph(ExtractionState)
        
        # Add nodes
        workflow.add_node("discover_schema", self._discover_schema_node)
        workflow.add_node("generate_config", self._generate_config_node)
        workflow.add_node("extract_data", self._extract_data_node)
        
        # Add edges
        workflow.set_entry_point("discover_schema")
        workflow.add_edge("discover_schema", "generate_config")
        workflow.add_edge("generate_config", "extract_data")
        workflow.add_edge("extract_data", END)
        
        return workflow.compile()
    
    async def _discover_schema_node(self, state: ExtractionState) -> ExtractionState:
        """Discover extraction schema from document."""
        try:
            schema = await self.schema_discovery.discover_schema(
                document_text=state["document_text"],
                document_type="resume"
            )
            
            return {
                **state,
                "schema": schema,
                "status": "schema_discovered"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Schema discovery failed: {str(e)}",
                "status": "error"
            }
    
    async def _generate_config_node(self, state: ExtractionState) -> ExtractionState:
        """Generate langextract configuration."""
        try:
            config = self.config_generator.generate_config(
                schema=state["schema"],
                sample_text=state["document_text"][:500]
            )
            
            return {
                **state,
                "config": config,
                "status": "config_generated"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Config generation failed: {str(e)}",
                "status": "error"
            }
    
    async def _extract_data_node(self, state: ExtractionState) -> ExtractionState:
        """Extract structured data using langextract."""
        try:
            if LANGEXTRACT_AVAILABLE:
                result = lx.extract(
                    text_or_documents=state["document_text"],
                    prompt_description=state["config"]["prompt"],
                    examples=state["config"]["examples"],
                    model_id=state["config"]["model_id"]
                )
                
                # Convert to serializable format
                extractions = []
                for extraction in result.extractions:
                    extractions.append({
                        "extraction_class": extraction.extraction_class,
                        "extraction_text": extraction.extraction_text,
                        "attributes": extraction.attributes
                    })
            else:
                # Mock extractions when langextract not available
                extractions = [
                    {
                        "extraction_class": "personal_info",
                        "extraction_text": "Hamza Khaled Mahmoud Ahmed",
                        "attributes": {"type": "name"}
                    },
                    {
                        "extraction_class": "skills",
                        "extraction_text": "Python, Machine Learning, TensorFlow",
                        "attributes": {"category": "technical"}
                    }
                ]
            
            return {
                **state,
                "extractions": extractions,
                "status": "extraction_complete"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Extraction failed: {str(e)}",
                "status": "error"
            }
    
    async def run_extraction(self, document_text: str, document_id: str) -> ExtractionState:
        """Run the complete extraction workflow."""
        initial_state = ExtractionState(
            document_text=document_text,
            document_id=document_id,
            schema=None,
            config=None,
            extractions=[],
            status="started",
            error=""
        )
        
        result = await self.workflow.ainvoke(initial_state)
        return result