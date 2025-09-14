"""
Custom Weave Model for Document Analysis Agent with token and cost tracking
"""


from weave import Model
import weave
from typing import Dict, Any, List
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from dotenv import load_dotenv
from ...tools import temporal_analysis_tools, line_item_analysis_tools
import logging

load_dotenv()
logger = logging.getLogger(f"{__name__}")
class DocumentAnalysisDeps(BaseModel):
    """Dependencies for the document analysis agent."""
    query: str



# TODO , AGENT GETS STUCK AND THE CODE CANNOT RUN , SO I AM THINKING IT's EITHER HE GETS CONFUSED OR IT IS A BUG, BUT HE WAS ABLE TO ANALYZE AND GET RESPONSES BEFORE.
class DocumentAnalysisModel(Model):
    """
    Custom Weave Model for Document Analysis with token and cost tracking.

    Pricing:
    - Input tokens: $0.15 per 1,000,000 tokens
    - Output tokens: $0.60 per 1,000,000 tokens
    """
    model_name: str = "gemini-2.0-flash"
    input_token_cost_per_million: float = 0.15
    output_token_cost_per_million: float = 0.40


    def __init__(self, **data):
        super().__init__(**data)

        # Initialize agent once as class field for performance
        self._cached_agent = self._create_agent()


    def _create_agent(self):
        """Create the pydantic-ai agent once during initialization."""
        agent = Agent(
            self.model_name,
            deps_type=DocumentAnalysisDeps,
            tools= line_item_analysis_tools+temporal_analysis_tools
        )

        # Set up the system prompt
        @agent.system_prompt
        def dynamic_system_prompt(ctx: RunContext[DocumentAnalysisDeps]) -> str:
            document_analysis_prompt = """
            You are a Document Analysis Agent that calls the appropriate tools based on user queries.

            ## Your Mission
            Call the correct tools to retrieve data. Do NOT provide analysis or interpretation - just call the tools and let them return their raw results.
            Do not call multiple tools , Only use one tool.
            ## Available Tools

            ### 🕐 Temporal Analysis Tools
            - **get_documents_by_date_range** - For date range queries
            - **get_documents_by_date_type** - For specific date type queries
            - **get_recent_temporal_data** - For recent temporal data
            - **get_temporal_statistics** - For temporal statistics

            ### 🛒 Line Item Analysis Tools
            - **get_line_items_by_document** - For document-specific line items
            - **get_line_items_by_amount_range** - For price range filtering
            - **get_recent_line_items** - For recent purchases
            - **search_line_items_by_description** - For product searches
            - **get_line_item_statistics** - For line item statistics

            ## Instructions
            1. Analyze the user query
            2. Call the appropriate tool(s)

            User Query: {query}
            """
            return document_analysis_prompt.format(query=ctx.deps.query)

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
    def _extract_raw_tool_results(self, result) -> List[Dict[str, Any]]:
        """Extract ONLY raw tool results from agent response."""
        raw_tool_results = []

        try:
            # Get all messages from the conversation
            messages = result.all_messages()

            for message in messages:
                # Look for tool call results
                if hasattr(message, 'parts'):
                    for part in message.parts:
                        if hasattr(part, 'tool_name') and hasattr(part, 'content'):
                            raw_tool_results.append({
                                "tool_name": part.tool_name,
                                "tool_result": part.content
                            })
        except Exception as e:
            # Return error if extraction fails
            return [{"error": f"Failed to extract tool results: {e}"}]

        return raw_tool_results

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
            logger.info(f"Running document analysis for query: {query}")

            # Use cached agent (initialized once) for performance
            deps = DocumentAnalysisDeps(query=query)

            # Execute the cached agent
            result = await self._cached_agent.run(query, deps=deps)
            logger.info(f"Query executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in run_document_analysis method: {e}")
            return {"error": str(e)}



    # HELPER FUNCTIONS
    def get_cost_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable cost summary."""
        costs = results.get("costs", {})
        usage = results.get("usage", {})

        return f"""
        Cost Summary:
        - Input tokens: {usage.get('input_tokens', 0):,} (${costs.get('input_cost_usd', 0):.6f})
        - Output tokens: {usage.get('output_tokens', 0):,} (${costs.get('output_cost_usd', 0):.6f}) [Tool outputs - no LLM cost]
        - Total cost: ${costs.get('total_cost_usd', 0):.6f}
                """.strip()

    def get_usage_stats(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage statistics from results."""
        return {
            "tokens": results.get("usage", {}),
            "costs": results.get("costs", {}),
            "model": results.get("model", self.model_name)
        }

async def demo_document_analysis_agent():
    """Demo function showing document analysis agent capabilities with cost tracking."""
    print("📊 DOCUMENT ANALYSIS AGENT DEMO WITH COST TRACKING")
    print("=" * 70)

    agent = DocumentAnalysisModel()

    # Show pricing info
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
            result = await agent.run_document_analysis(query)
            print(result)
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