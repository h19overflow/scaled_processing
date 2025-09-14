"""
Custom Weave Model for Document Analysis Agent with token and cost tracking
"""

from weave import Model
import weave
from typing import Dict, Any, List
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

from .document_analysis_prompt import DOCUMENT_ANALYSIS_PROMPT
from ...tools import temporal_analysis_tools, line_item_analysis_tools


class DocumentAnalysisDeps(BaseModel):
    """Dependencies for the document analysis agent."""
    query: str


class DocumentAnalysisModel(Model):
    """
    Custom Weave Model for Document Analysis with token and cost tracking.

    Pricing:
    - Input tokens: $0.15 per 1,000,000 tokens
    - Output tokens: $0.60 per 1,000,000 tokens
    """

    model_name: str = "gemini-2.0-flash"
    input_token_cost_per_million: float = 0.15
    output_token_cost_per_million: float = 0.60

    def _initialize_agent(self):
        """Initialize the pydantic-ai agent."""
        agent = Agent(
            self.model_name,
            deps_type=DocumentAnalysisDeps,
            tools=temporal_analysis_tools + line_item_analysis_tools
        )

        # Set up the system prompt
        @agent.system_prompt
        def dynamic_system_prompt(ctx: RunContext[DocumentAnalysisDeps]) -> str:
            return DOCUMENT_ANALYSIS_PROMPT.format(query=ctx.deps.query)

        return agent

    def simple_token_count(self, text: str) -> int:
        """Simple token counting logic - approximate tokens as words/characters."""
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(str(text)) // 4

    def calculate_costs(self, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Calculate costs based on token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_token_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_token_cost_per_million
        total_cost = input_cost + output_cost

        return {
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6)
        }

    @weave.op()
    async def run_document_analysis(self, query: str) -> Dict[str, Any]:
        """
        Run document analysis and track token usage and costs.

        Args:
            query: User's natural language query

        Returns:
            Dict with tool results, usage stats, and cost information
        """
        try:
            # Initialize agent for this request
            agent = self._initialize_agent()

            # Prepare input
            deps = DocumentAnalysisDeps(query=query)

            # Calculate input tokens (query + prompt)
            full_prompt = DOCUMENT_ANALYSIS_PROMPT.format(query=query)
            input_tokens = self.simple_token_count(query + full_prompt)

            # Execute the agent
            result = await agent.run(query, deps=deps)

            # Calculate output tokens from tool results
            output_data = result.data if hasattr(result, 'data') else {}
            output_tokens = self.simple_token_count(str(output_data))

            # Calculate costs
            costs = self.calculate_costs(input_tokens, output_tokens)

            return {
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                "costs": costs,
                "model": self.model_name,
                "tool_results": output_data,
                "query": query
            }

        except Exception as e:
            # Return error with minimal token usage for the error message
            error_tokens = self.simple_token_count(str(e))
            costs = self.calculate_costs(0, error_tokens)

            return {
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": error_tokens,
                    "total_tokens": error_tokens,
                },
                "costs": costs,
                "model": self.model_name,
                "tool_results": {"error": f"Failed to execute query: {e}"},
                "query": query
            }

    @weave.op()
    def predict(self, query: str) -> Dict[str, Any]:
        """
        Synchronous prediction interface for Weave compatibility.

        Args:
            query: User's natural language query

        Returns:
            Dict with analysis results and cost tracking
        """
        import asyncio
        return asyncio.run(self.run_document_analysis(query))

    # HELPER FUNCTIONS
    def get_cost_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable cost summary."""
        costs = results.get("costs", {})
        usage = results.get("usage", {})

        return f"""
Cost Summary:
- Input tokens: {usage.get('input_tokens', 0):,} (${costs.get('input_cost_usd', 0):.6f})
- Output tokens: {usage.get('output_tokens', 0):,} (${costs.get('output_cost_usd', 0):.6f})
- Total cost: ${costs.get('total_cost_usd', 0):.6f}
        """.strip()

    def get_usage_stats(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage statistics from results."""
        return {
            "tokens": results.get("usage", {}),
            "costs": results.get("costs", {}),
            "model": results.get("model", self.model_name)
        }