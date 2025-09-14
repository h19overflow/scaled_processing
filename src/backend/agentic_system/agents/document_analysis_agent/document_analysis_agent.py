"""
Document Analysis Agent for comprehensive document and data analysis using temporal and line item tools
"""

import os
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .document_analysis_prompt import DOCUMENT_ANALYSIS_PROMPT
from ...tools import temporal_analysis_tools, line_item_analysis_tools

from dotenv import load_dotenv
load_dotenv()
import weave
weave.init(project_name='scaled_processing')
class DocumentAnalysisDeps(BaseModel):
    """
    Dependencies for the document analysis agent.
    """
    query: str


document_analysis_agent = Agent(
    'gemini-2.0-flash',
    deps_type=DocumentAnalysisDeps,
    tools=temporal_analysis_tools + line_item_analysis_tools,
)


@document_analysis_agent.system_prompt
def dynamic_system_prompt(ctx: RunContext[DocumentAnalysisDeps]) -> str:
    """
    Create custom instructions for the document analysis agent.

    Args:
        ctx: The context containing the query to analyze

    Returns:
        str: The complete instructions for the AI agent
    """
    return DOCUMENT_ANALYSIS_PROMPT.format(query=ctx.deps.query)


class DocumentAnalysisAgent:
    """
    The main document analysis agent class for comprehensive document and data analysis.
    """

    def __init__(self):
        """
        Initialize the document analysis agent.
        """
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

    @weave.op()
    async def run_query(self, query: str) -> Any:
        """
        Run a query and let the agent execute the appropriate tools.

        Args:
            query: The user's natural language query

        Returns:
            Any: Raw tool outputs based on the query
        """
        try:
            deps = DocumentAnalysisDeps(query=query)

            result = await document_analysis_agent.run(
                query,
                deps=deps
            )

            return result.data

        except Exception as e:
            return {"error": f"Failed to execute query: {e}"}

    @weave.op()
    async def get_tool_outputs(self, query: str) -> Dict[str, Any]:
        """
        Get raw tool outputs for external processing.

        Args:
            query: The user's natural language query

        Returns:
            Dict with query and raw tool results
        """
        tool_outputs = await self.run_query(query)
        return {
            "query": query,
            "tool_results": tool_outputs
        }


async def demo_document_analysis_agent():
    """Demo function showing document analysis agent capabilities."""
    print("📊 DOCUMENT ANALYSIS AGENT DEMO")
    print("=" * 60)

    agent = DocumentAnalysisAgent()

    demo_queries = [
        "Show me recent line items from the last 7 days",
        "What are our most expensive purchases over $500?",
        "Give me statistics on temporal data",
        "Find all products containing 'adhesive' in their description",
        "Show me documents from the last month"
    ]

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 40)

        try:
            # Get raw tool outputs
            result = await agent.get_tool_outputs(query)
            print(f"Query: {result['query']}")
            print(f"Tool Results: {result['tool_results']}")

            # You can now process these raw results however you want
            # For demo purposes, just show the raw data structure

        except Exception as e:
            print(f"Error: {e}")

        print()

    print("✅ Demo completed - Raw tool outputs retrieved!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_document_analysis_agent())