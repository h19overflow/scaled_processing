"""
Document Analysis Agent for comprehensive document and data analysis using temporal and line item tools
"""

import os
from typing import Optional, Dict, Any
import weave

from .document_analysis_model import DocumentAnalysisModel

from dotenv import load_dotenv
load_dotenv()

weave.init(project_name='scaled_processing')


class DocumentAnalysisAgent:
    """
    The main document analysis agent class with token and cost tracking.
    """

    def __init__(self):
        """
        Initialize the document analysis agent with Weave model.
        """
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.model = DocumentAnalysisModel()

    @weave.op()
    async def run_query(self, query: str) -> Dict[str, Any]:
        """
        Run a query with full cost and usage tracking.

        Args:
            query: The user's natural language query

        Returns:
            Dict with tool results, usage stats, and costs
        """
        return await self.model.run_document_analysis(query)

    @weave.op()
    async def get_tool_outputs(self, query: str) -> Dict[str, Any]:
        """
        Get raw tool outputs for external processing with cost tracking.

        Args:
            query: The user's natural language query

        Returns:
            Dict with query, tool results, and cost information
        """
        result = await self.run_query(query)
        return {
            "query": query,
            "tool_results": result.get("tool_results", {}),
            "usage": result.get("usage", {}),
            "costs": result.get("costs", {}),
            "cost_summary": self.model.get_cost_summary(result)
        }

    def get_pricing_info(self) -> Dict[str, float]:
        """Get current pricing information."""
        return {
            "input_token_cost_per_million": self.model.input_token_cost_per_million,
            "output_token_cost_per_million": self.model.output_token_cost_per_million,
            "model_name": self.model.model_name
        }


async def demo_document_analysis_agent():
    """Demo function showing document analysis agent capabilities with cost tracking."""
    print("📊 DOCUMENT ANALYSIS AGENT DEMO WITH COST TRACKING")
    print("=" * 70)

    agent = DocumentAnalysisAgent()

    # Show pricing info
    pricing = agent.get_pricing_info()
    print(f"💰 Pricing Info:")
    print(f"   Model: {pricing['model_name']}")
    print(f"   Input tokens: ${pricing['input_token_cost_per_million']:.2f} per 1M tokens")
    print(f"   Output tokens: ${pricing['output_token_cost_per_million']:.2f} per 1M tokens")
    print()

    demo_queries = [
        "Show me recent line items from the last 7 days",
        "What are our most expensive purchases over $500?",
        "Give me statistics on temporal data",
        "Find all products containing 'adhesive' in their description",
        "Show me documents from the last month"
    ]

    total_cost = 0.0
    total_tokens = 0

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 50)

        try:
            # Get results with cost tracking
            result = await agent.get_tool_outputs(query)

            print(f"✅ Query executed successfully")
            print(f"🔧 Tool Results: {len(str(result['tool_results']))} characters of data")

            # Show usage and costs
            usage = result['usage']
            costs = result['costs']

            print(f"📊 Usage:")
            print(f"   Input tokens: {usage.get('input_tokens', 0):,}")
            print(f"   Output tokens: {usage.get('output_tokens', 0):,}")
            print(f"   Total tokens: {usage.get('total_tokens', 0):,}")

            print(f"💵 Cost:")
            print(f"   Input cost: ${costs.get('input_cost_usd', 0):.6f}")
            print(f"   Output cost: ${costs.get('output_cost_usd', 0):.6f}")
            print(f"   Query total: ${costs.get('total_cost_usd', 0):.6f}")

            # Accumulate totals
            total_cost += costs.get('total_cost_usd', 0)
            total_tokens += usage.get('total_tokens', 0)

        except Exception as e:
            print(f"❌ Error: {e}")

        print()

    print("=" * 70)
    print(f"📈 Session Summary:")
    print(f"   Total tokens used: {total_tokens:,}")
    print(f"   Total session cost: ${total_cost:.6f}")
    print(f"   Average cost per query: ${total_cost/len(demo_queries):.6f}")
    print("✅ Demo completed - All queries executed with cost tracking!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_document_analysis_agent())