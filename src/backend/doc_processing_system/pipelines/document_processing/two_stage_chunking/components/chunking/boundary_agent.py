"""
Boundary Review Agent - Stage 2 of 2-stage chunking system

Uses LLM to review chunk boundaries and decide whether to merge or keep splits.
Analyzes boundary text to determine if thoughts continue across chunk boundaries.

Dependencies: pydantic-ai, gemini-2.5-flash-lite
Integration: Used by TwoStageChunker for boundary refinement
"""

import os
import asyncio
import logging
import time
from typing import Dict, Any, List, Literal
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()


class BoundaryDecision(BaseModel):
    """Model for boundary review decision."""
    decision: str = Literal['MERGE', 'KEEP']
    confidence: float  # 0.0 to 1.0


class BoundaryReviewDeps(BaseModel):
    """Dependencies for boundary review agent."""
    boundary_text: str
    chunk_index: int


# Note: Agent and system prompt are created dynamically in the BoundaryReviewAgent class


class BoundaryReviewAgent:
    """Agent for reviewing chunk boundaries and making merge/keep decisions."""
    
    def __init__(self, context_window: int = 200, model_name: str = "gemini-2.0-flash"):
        """Initialize boundary review agent.
        
        Args:
            context_window: Number of chars to include before/after boundary
            model_name: LLM model to use for boundary decisions
        """
        self.context_window = context_window
        self.model_name = model_name
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Set API key
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        
        # Create the agent dynamically with specified model
        self.agent = Agent(
            model=self.model_name,
            result_type=BoundaryDecision,
            deps_type=BoundaryReviewDeps,
        )
        
        # Define system prompt for the agent
        @self.agent.system_prompt
        def boundary_system_prompt(ctx: RunContext[BoundaryReviewDeps]) -> str:
            return f"""You are a boundary review specialist. Your job is to analyze chunk boundaries and determine if they represent natural break points in the text.

TASK: Review the text snippet below and decide if the boundary marked with [BOUNDARY] represents a logical split point.

DECISION RULES:
- MERGE: If the text flows naturally across the boundary (same topic, continuing thought, mid-sentence, etc.)
- KEEP: If the boundary represents a clear topic change, section break, or natural pause

TEXT TO ANALYZE:
{ctx.deps.boundary_text}

Respond with:
- decision: "MERGE" or "KEEP"
- confidence: float between 0.0-1.0 

Be concise and decisive. Focus on semantic continuity across the boundary."""
        
        self.logger.info(f"🤖 Boundary review agent initialized (context_window={context_window}, model={model_name})")
    
    def create_boundary_text(self, chunk1: str, chunk2: str) -> str:
        """Create boundary text snippet for analysis.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            Text snippet with boundary marker
        """
        # Get context from end of chunk1 and beginning of chunk2
        end_context = chunk1[-self.context_window:] if len(chunk1) > self.context_window else chunk1
        start_context = chunk2[:self.context_window] if len(chunk2) > self.context_window else chunk2
        
        # Create boundary text with marker
        boundary_text = f"{end_context}\n[BOUNDARY]\n{start_context}"
        
        return boundary_text
    
    async def review_boundary(self, chunk1: str, chunk2: str, chunk_index: int) -> Dict[str, Any]:
        """Review a boundary between two chunks.
        
        Args:
            chunk1: First chunk text
            chunk2: Second chunk text
            chunk_index: Index of the boundary being reviewed
            
        Returns:
            Dict containing decision and metadata
        """
        start_time = time.time()
        
        try:
            # Create boundary text for analysis
            boundary_text = self.create_boundary_text(chunk1, chunk2)
            
            # Create dependencies
            deps = BoundaryReviewDeps(
                boundary_text=boundary_text,
                chunk_index=chunk_index
            )
            
            # Get agent decision with timeout to prevent hanging
            result = await asyncio.wait_for(
                self.agent.run(
                    "Review this boundary and decide whether to merge or keep the chunks.",
                    deps=deps
                ),
                timeout=10.0  # 10 second timeout per boundary
            )
            
            decision_data = result.data
            processing_time = time.time() - start_time
            
            review_result = {
                "decision": decision_data.decision,
                "confidence": decision_data.confidence,
                "chunk_index": chunk_index,
                "processing_time_seconds": round(processing_time, 3),
                "boundary_text_length": len(boundary_text),
                "model_name": self.model_name,
                "status": "success"
            }
            
            self.logger.debug(f"🔍 Boundary {chunk_index}: {decision_data.decision} (conf={decision_data.confidence:.2f})")
            return review_result
            
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Boundary review timeout for index {chunk_index}")
            
            return {
                "decision": "KEEP",  # Conservative default on timeout
                "confidence": 0.0,
                "chunk_index": chunk_index,
                "processing_time_seconds": round(processing_time, 3),
                "model_name": self.model_name,
                "status": "error",
                "error": "Request timeout (10s)"
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Return default decision on error
            self.logger.error(f"❌ Boundary review failed for index {chunk_index}: {e}")
            
            return {
                "decision": "KEEP",  # Conservative default
                "confidence": 0.0,
                "chunk_index": chunk_index,
                "processing_time_seconds": round(processing_time, 3),
                "model_name": self.model_name,
                "status": "error",
                "error": str(e)
            }
    
    async def review_all_boundaries(self, chunks: List[str], max_concurrent: int = 10) -> Dict[str, Any]:
        """Review all boundaries between adjacent chunks with concurrent processing.
        
        Args:
            chunks: List of text chunks
            max_concurrent: Maximum number of concurrent boundary reviews
            
        Returns:
            Dict containing all boundary decisions and statistics
        """
        start_time = time.time()
        
        if len(chunks) <= 1:
            return {
                "boundary_decisions": [],
                "total_boundaries": 0,
                "merge_decisions": 0,
                "keep_decisions": 0,
                "error_decisions": 0,
                "processing_time_seconds": 0.0,
                "avg_confidence": 0.0,
                "concurrent_agents": 0
            }
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def review_boundary_with_semaphore(i: int) -> Dict[str, Any]:
            """Review boundary with concurrency control."""
            async with semaphore:
                chunk1 = chunks[i]
                chunk2 = chunks[i + 1]
                return await self.review_boundary(chunk1, chunk2, i)
        
        # Create all boundary review tasks
        tasks = []
        for i in range(len(chunks) - 1):
            task = review_boundary_with_semaphore(i)
            tasks.append(task)
        
        self.logger.info(f"🚀 Starting {len(tasks)} boundary reviews with {max_concurrent} concurrent agents")
        
        # Execute all boundary reviews concurrently with proper exception handling
        try:
            boundary_decisions = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"❌ Async gather failed: {e}")
            # Create fallback results
            boundary_decisions = [Exception(f"Gather failed: {e}") for _ in range(len(tasks))]
        
        # Handle any exceptions and ensure all results are dicts
        processed_decisions = []
        for i, result in enumerate(boundary_decisions):
            if isinstance(result, Exception):
                # Handle exception case
                self.logger.error(f"❌ Boundary review {i} failed: {result}")
                processed_decisions.append({
                    "decision": "KEEP",
                    "confidence": 0.0,
                    "chunk_index": i,
                    "processing_time_seconds": 0.0,
                    "model_name": self.model_name,
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_decisions.append(result)
        
        # Calculate statistics
        total_time = time.time() - start_time
        merge_count = sum(1 for d in processed_decisions if d["decision"] == "MERGE")
        keep_count = sum(1 for d in processed_decisions if d["decision"] == "KEEP") 
        error_count = sum(1 for d in processed_decisions if d["status"] == "error")
        
        confidences = [d["confidence"] for d in processed_decisions if d["status"] == "success"]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        result = {
            "boundary_decisions": processed_decisions,
            "total_boundaries": len(processed_decisions),
            "merge_decisions": merge_count,
            "keep_decisions": keep_count,
            "error_decisions": error_count,
            "processing_time_seconds": round(total_time, 3),
            "avg_confidence": round(avg_confidence, 3),
            "concurrent_agents": max_concurrent,
            "model_name": self.model_name
        }
        
        self.logger.info(f"🤖 Reviewed {len(processed_decisions)} boundaries: {merge_count} merge, {keep_count} keep, {error_count} errors")
        self.logger.info(f"⚡ Concurrent processing: {max_concurrent} agents, {total_time:.3f}s total")
        
        return result