"""
Multi-agent LangGraph workflow for comprehensive structured extraction.
Processes entire documents using chunking, sequential discovery, and consolidation.
"""

import json
import asyncio
from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from .document_chunker import DocumentChunker, DocumentChunk
from .sequential_schema_discovery import SequentialSchemaDiscovery, ProgressiveSchema
from .schema_consolidation import SchemaConsolidation, ConsolidatedSchema
from .config_generator import ConfigGenerator
from .models import DocumentSchema

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

class MultiAgentState(TypedDict):
    """State for the multi-agent extraction workflow."""
    document_text: str
    document_id: str
    chunks: List[DocumentChunk]
    progressive_results: List[ProgressiveSchema]
    consolidated_schema: ConsolidatedSchema
    final_schema: DocumentSchema
    config: Dict[str, Any]
    extractions: List[Dict[str, Any]]
    status: str
    error: str

class MultiAgentWorkflow:
    """Comprehensive multi-agent workflow for document extraction."""
    
    def __init__(self, max_tokens: int = 1500, max_fields: int = 8):
        """Initialize multi-agent workflow."""
        self.chunker = DocumentChunker(max_tokens=max_tokens)
        self.sequential_discovery = SequentialSchemaDiscovery()
        self.consolidation = SchemaConsolidation()
        self.config_generator = ConfigGenerator()
        self.max_fields = max_fields
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the multi-agent workflow graph."""
        workflow = StateGraph(MultiAgentState)
        
        # Add nodes
        workflow.add_node("chunk_document", self._chunk_document_node)
        workflow.add_node("sequential_discovery", self._sequential_discovery_node)
        workflow.add_node("consolidate_schema", self._consolidate_schema_node)
        workflow.add_node("generate_config", self._generate_config_node)
        workflow.add_node("extract_data", self._extract_data_node)
        
        # Add edges
        workflow.set_entry_point("chunk_document")
        workflow.add_edge("chunk_document", "sequential_discovery")
        workflow.add_edge("sequential_discovery", "consolidate_schema")
        workflow.add_edge("consolidate_schema", "generate_config")
        workflow.add_edge("generate_config", "extract_data")
        workflow.add_edge("extract_data", END)
        
        return workflow.compile()
    
    async def _chunk_document_node(self, state: MultiAgentState) -> MultiAgentState:
        """Chunk document into processing batches."""
        try:
            chunks = self.chunker.chunk_document(
                text=state["document_text"],
                document_id=state["document_id"]
            )
            
            chunk_summary = self.chunker.get_chunk_summary(chunks)
            print(f"📄 Created {len(chunks)} chunks, {chunk_summary['total_tokens']} total tokens")
            
            return {
                **state,
                "chunks": chunks,
                "status": "chunked"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Document chunking failed: {str(e)}",
                "status": "error"
            }
    
    async def _sequential_discovery_node(self, state: MultiAgentState) -> MultiAgentState:
        """Process chunks sequentially to discover schemas."""
        try:
            # Reset discovery state
            self.sequential_discovery.reset()
            
            print("🔍 Starting sequential schema discovery...")
            progressive_results = await self.sequential_discovery.process_all_chunks(
                chunks=state["chunks"],
                document_type="unknown"
            )
            
            total_fields = len(self.sequential_discovery.discovered_fields)
            print(f"✨ Discovered {total_fields} fields across {len(progressive_results)} chunks")
            
            return {
                **state,
                "progressive_results": progressive_results,
                "status": "discovery_complete"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Sequential discovery failed: {str(e)}",
                "status": "error"
            }
    
    async def _consolidate_schema_node(self, state: MultiAgentState) -> MultiAgentState:
        """Consolidate discovered schemas into final optimized schema."""
        try:
            print("🔧 Consolidating discovered schemas...")
            
            # Validate discovered fields before consolidation
            if not self.sequential_discovery.discovered_fields or len(self.sequential_discovery.discovered_fields) == 0:
                raise ValueError("No fields discovered to consolidate")
            
            consolidated = await self.consolidation.consolidate_schema(
                discovered_fields=self.sequential_discovery.discovered_fields,
                document_type=self.sequential_discovery.document_type,
                max_fields=self.max_fields
            )
            
            final_schema = self.consolidation.to_document_schema(consolidated)
            
            # Validate final schema
            if not final_schema or len(final_schema.extraction_classes) == 0:
                raise ValueError("Schema consolidation produced no extraction classes")
            
            print(f"📊 Consolidated to {len(final_schema.extraction_classes)} final fields")
            print(f"📋 Document type: {final_schema.document_type}")
            
            return {
                **state,
                "consolidated_schema": consolidated,
                "final_schema": final_schema,
                "status": "consolidated"
            }
            
        except Exception as e:
            return {
                **state,
                "error": f"Schema consolidation failed: {str(e)}",
                "status": "error"
            }
    
    async def _generate_config_node(self, state: MultiAgentState) -> MultiAgentState:
        """Generate langextract configuration from final schema."""
        try:
            config = self.config_generator.generate_config(
                schema=state["final_schema"],
                sample_text=state["document_text"][:1000]
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
    
    async def _extract_data_node(self, state: MultiAgentState) -> MultiAgentState:
        """Extract structured data using langextract with final schema."""
        try:
            print("⚡ Running final extraction with consolidated schema...")
            
            if LANGEXTRACT_AVAILABLE:
                # Validate inputs before extraction
                if not state["document_text"] or len(state["document_text"].strip()) < 100:
                    raise ValueError("Document text is too short or empty")
                
                if not state["config"]["examples"] or len(state["config"]["examples"]) == 0:
                    raise ValueError("No examples provided for extraction")
                
                result = lx.extract(
                    text_or_documents=state["document_text"],
                    prompt_description=state["config"]["prompt"],
                    examples=state["config"]["examples"],
                    model_id=state["config"]["model_id"]
                )
                
                if not result or not hasattr(result, 'extractions'):
                    raise ValueError("LangExtract returned invalid result")
                
                extractions = []
                for extraction in result.extractions:
                    # Filter out empty or null extractions
                    if (extraction.extraction_text and 
                        extraction.extraction_text.strip() and 
                        extraction.extraction_text.lower() not in ['null', 'none', 'n/a', ''] and
                        len(extraction.extraction_text.strip()) > 5):  # Minimum meaningful length
                        extractions.append({
                            "extraction_class": extraction.extraction_class,
                            "extraction_text": extraction.extraction_text.strip(),
                            "attributes": extraction.attributes
                        })
                
                # Ensure we have meaningful extractions
                if len(extractions) == 0:
                    raise ValueError("No valid extractions found - all extractions were empty or invalid")
            else:
                # Mock extractions based on schema
                extractions = []
                for field in state["final_schema"].extraction_classes[:3]:
                    extractions.append({
                        "extraction_class": field.field_name,
                        "extraction_text": field.example_text,
                        "attributes": field.attributes
                    })
            
            print(f"✅ Extracted {len(extractions)} structured items")
            
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
    
    async def run_extraction(self, document_text: str, document_id: str) -> MultiAgentState:
        """Run the complete multi-agent extraction workflow."""
        initial_state = MultiAgentState(
            document_text=document_text,
            document_id=document_id,
            chunks=[],
            progressive_results=[],
            consolidated_schema=None,
            final_schema=None,
            config=None,
            extractions=[],
            status="started",
            error=""
        )
        
        print(f"🚀 Starting multi-agent extraction for: {document_id}")
        result = await self.workflow.ainvoke(initial_state)
        return result