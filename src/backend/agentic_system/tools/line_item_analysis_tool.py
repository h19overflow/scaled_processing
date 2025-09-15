# """
# Line Item Analysis Tool for agentic systems.
# Converts LineItemCRUD operations into pydantic-ai tools for product and pricing analysis.
# """
#
# from typing import List, Dict, Any, Optional
# from pydantic_ai import Tool
# from pydantic import BaseModel, Field
#
# from ...doc_processing_system.core_deps.database.connection_manager import ConnectionManager
# from ...doc_processing_system.core_deps.database.CRUD.line_item_crud import LineItemCRUD
# import weave
# weave.init(project_name='scaled_processing')
# class DocumentLineItemQuery(BaseModel):
#     """Parameters for getting line items from a specific document."""
#     document_id: str = Field(description="Document UUID to get line items for")
#     limit: int = Field(default=100, description="Maximum records to return (1-500)")
#
#
# class AmountRangeQuery(BaseModel):
#     """Parameters for filtering line items by amount range."""
#     min_amount: float = Field(description="Minimum total amount")
#     max_amount: float = Field(description="Maximum total amount")
#     limit: int = Field(default=100, description="Maximum records to return (1-500)")
#
#
# class RecentLineItemQuery(BaseModel):
#     """Parameters for getting recent line items."""
#     days: int = Field(default=7, description="Number of recent days to query (1-90)")
#     limit: int = Field(default=50, description="Maximum records to return (1-200)")
#
#
# class DescriptionSearchQuery(BaseModel):
#     """Parameters for searching line items by description."""
#     keyword: str = Field(description="Search term for product description")
#     limit: int = Field(default=50, description="Maximum records to return (1-200)")
#
#
# class LineItemAnalysisTool:
#     """
#     Line Item Analysis Tool for extracting and analyzing product/pricing information from documents.
#
#     This tool provides access to line item data extracted from invoices, receipts, and purchase orders:
#     - Product descriptions and details
#     - Pricing information (unit price, quantity, total amount)
#     - Currency and financial data
#     - Search and filtering capabilities
#
#     WHEN TO USE:
#     - User asks about products, items, or merchandise
#     - Pricing and financial analysis questions
#     - Questions like "Show me expensive items" or "Find products containing 'adhesive'"
#     - Invoice line item analysis: "What items are on this invoice?"
#     - Budget analysis: "Show me items over $500"
#     - Product search: "Find all computer-related purchases"
#
#     WHEN NOT TO USE:
#     - General document search without product focus
#     - Date-based queries (use temporal tool instead)
#     - Questions about document metadata or structure
#     - User wants full document content (use document retrieval instead)
#     - Non-commercial documents without line items
#     """
#
#     def __init__(self):
#         """Initialize the line item analysis tool with database connection."""
#         self.connection_manager = ConnectionManager()
#         self.line_item_crud = LineItemCRUD(self.connection_manager)
#     @weave.op()
#     async def get_line_items_by_document(self, query: DocumentLineItemQuery) -> List[Dict[str, Any]]:
#         """
#         Get all line items for a specific document.
#
#         Use this when:
#         - User asks about items in a specific document
#         - Analyzing contents of a particular invoice/receipt
#         - Questions like "What's on invoice XYZ?" or "Show me items from this document"
#
#         Args:
#             query: DocumentLineItemQuery with document_id and optional limit
#
#         Returns:
#             List of structured line item records with:
#             - product: {description, raw_text}
#             - pricing: {quantity, unit_price, total_amount, currency}
#             - display: {formatted text versions for UI}
#             - metadata: {timestamps, flags}
#
#         Example queries:
#         - "Show me all items from document abc-123"
#         - "What products are in this invoice?"
#         - "List line items for this receipt"
#         """
#         try:
#             return self.line_item_crud.get_line_items_by_document(
#                 document_id=query.document_id,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve line items for document: {str(e)}"}]
#
#     weave.op()
#     async def get_line_items_by_amount_range(self, query: AmountRangeQuery) -> List[Dict[str, Any]]:
#         """
#         Get line items within a specified amount range.
#
#         Use this when:
#         - User asks about expensive or cheap items
#         - Budget analysis and financial filtering
#         - Questions like "Show me items over $100" or "Find purchases between $50-$200"
#
#         Args:
#             query: AmountRangeQuery with min_amount, max_amount, and optional limit
#
#         Returns:
#             List of line items within the amount range, ordered by total amount (highest first)
#
#         Example queries:
#         - "Show me all items costing between $100 and $500"
#         - "Find expensive purchases over $1000"
#         - "What are the cheapest items we bought?"
#         """
#         try:
#             return self.line_item_crud.get_line_items_by_amount_range(
#                 min_amount=query.min_amount,
#                 max_amount=query.max_amount,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve line items by amount range: {str(e)}"}]
#
#     weave.op()
#     async def get_recent_line_items(self, query: RecentLineItemQuery) -> List[Dict[str, Any]]:
#         """
#         Get recent line items from the last N days.
#
#         Use this when:
#         - User asks about recent purchases or activity
#         - Analyzing recent spending patterns
#         - Questions like "What did we buy recently?" or "Show me this week's purchases"
#
#         Args:
#             query: RecentLineItemQuery with days and optional limit
#
#         Returns:
#             List of recent line item records ordered by creation date (newest first)
#
#         Example queries:
#         - "Show me items purchased in the last 7 days"
#         - "What line items were processed recently?"
#         - "Find recent purchases this month"
#         """
#         try:
#             return self.line_item_crud.get_recent_line_items(
#                 days=query.days,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve recent line items: {str(e)}"}]
#
#     weave.op()
#     async def search_line_items_by_description(self, query: DescriptionSearchQuery) -> List[Dict[str, Any]]:
#         """
#         Search line items by product description keyword.
#
#         Use this when:
#         - User searches for specific products or categories
#         - Finding items containing certain words
#         - Questions like "Find all computer equipment" or "Show me items with 'adhesive'"
#
#         Args:
#             query: DescriptionSearchQuery with keyword and optional limit
#
#         Returns:
#             List of matching line item records ordered by creation date (newest first)
#
#         Example queries:
#         - "Find all items containing 'computer'"
#         - "Search for adhesive products"
#         - "Show me all office supplies"
#         """
#         try:
#             return self.line_item_crud.search_line_items_by_description(
#                 keyword=query.keyword,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to search line items by description: {str(e)}"}]
#
#     weave.op()
#     async def get_line_item_statistics(self) -> Dict[str, Any]:
#         """
#         Get comprehensive line item statistics.
#
#         Use this when:
#         - User wants overview of line item data
#         - Statistical analysis of purchases and products
#         - Questions like "How many line items do we have?" or "What's our purchase summary?"
#
#         Returns:
#             Dictionary with line item statistics including:
#             - total_line_items: Total count of line items
#             - documents_with_line_items: Number of documents containing line items
#             - avg_items_per_document: Average line items per document
#             - currency_breakdown: Count of items by currency
#             - generated_at: When statistics were generated
#
#         Example queries:
#         - "Give me stats on line items"
#         - "How many products have been processed?"
#         - "What currencies are most common in our purchases?"
#         """
#         try:
#             return self.line_item_crud.get_line_item_statistics()
#         except Exception as e:
#             return {"error": f"Failed to retrieve line item statistics: {str(e)}"}
#
#
# # Create the pydantic-ai tools
# def create_line_item_tools() -> List[Tool]:
#     """
#     Create all line item analysis tools for pydantic-ai agents.
#
#     Returns:
#         List of Tool objects for line item data analysis
#     """
#     line_item_tool = LineItemAnalysisTool()
#
#     tools = [
#         Tool(
#             line_item_tool.get_line_items_by_document,
#             name="get_line_items_by_document",
#             description="""Get all line items for a specific document. Use when user asks about items in a particular invoice, receipt, or purchase order. Requires document_id."""
#         ),
#         Tool(
#             line_item_tool.get_line_items_by_amount_range,
#             name="get_line_items_by_amount_range",
#             description="""Get line items within a specific price range. Use when user asks about expensive/cheap items, budget analysis, or wants to filter by amount. Requires min_amount and max_amount."""
#         ),
#         Tool(
#             line_item_tool.get_recent_line_items,
#             name="get_recent_line_items",
#             description="""Get recent line items from the last N days. Use when user asks about recent purchases, latest activity, or wants to analyze recent spending patterns."""
#         ),
#         Tool(
#             line_item_tool.search_line_items_by_description,
#             name="search_line_items_by_description",
#             description="""Search line items by product description keyword. Use when user searches for specific products, categories, or items containing certain words. Requires keyword."""
#         ),
#         Tool(
#             line_item_tool.get_line_item_statistics,
#             name="get_line_item_statistics",
#             description="""Get comprehensive statistics about line item data including totals, currency breakdown, and averages. Use when user wants overview or statistical analysis of purchases and products."""
#         )
#     ]
#
#     return tools
#
#
# # Export the tools for easy import
# line_item_analysis_tools = create_line_item_tools()