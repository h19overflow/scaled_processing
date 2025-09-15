# """
# Temporal Analysis Tool for agentic systems.
# Converts TemporalCRUD operations into pydantic-ai tools for date-based document analysis.
# """
#
# from typing import List, Dict, Any, Optional
# from datetime import datetime, timedelta
# from pydantic_ai import Tool
# from pydantic import BaseModel, Field
#
# from ...doc_processing_system.core_deps.database.connection_manager import ConnectionManager
# from ...doc_processing_system.core_deps.database.CRUD.temporal_crud import TemporalCRUD
# import weave
# weave.init(project_name='scaled_processing')
# class DateRangeQuery(BaseModel):
#     """Parameters for querying documents within a date range."""
#     start_date: str = Field(description="Start date in YYYY-MM-DD format")
#     end_date: str = Field(description="End date in YYYY-MM-DD format")
#     limit: int = Field(default=100, description="Maximum records to return (1-1000)")
#
#
# class DateTypeQuery(BaseModel):
#     """Parameters for querying documents by date type."""
#     date_type: str = Field(description="Type of date (invoice_date, due_date, etc.)")
#     limit: int = Field(default=100, description="Maximum records to return (1-1000)")
#
#
# class RecentDataQuery(BaseModel):
#     """Parameters for querying recent temporal data."""
#     days: int = Field(default=7, description="Number of recent days to query (1-365)")
#     limit: int = Field(default=50, description="Maximum records to return (1-500)")
#
#
# class TemporalAnalysisTool:
#     """
#     Temporal Analysis Tool for extracting and analyzing date-based information from documents.
#
#     This tool provides access to temporal data extracted from documents, including:
#     - Invoice dates, due dates, payment dates
#     - Contract start/end dates
#     - Event dates and timelines
#     - Date ranges and temporal patterns
#
#     WHEN TO USE:
#     - User asks about dates, timelines, or temporal information
#     - Questions like "Show me invoices from last month"
#     - Date range queries: "Find documents between March and June 2023"
#     - Temporal analysis: "What's the average time between invoice and payment?"
#     - Recent activity queries: "What documents were processed recently?"
#
#     WHEN NOT TO USE:
#     - General document search without date criteria
#     - Questions about document content (not dates)
#     - Non-temporal queries about products, amounts, or descriptions
#     - User wants specific document content (use document retrieval instead)
#     """
#
#     def __init__(self):
#         """Initialize the temporal analysis tool with database connection."""
#         self.connection_manager = ConnectionManager()
#         self.temporal_crud = TemporalCRUD(self.connection_manager)
#
#     weave.op()
#     async def get_documents_by_date_range(self, query: DateRangeQuery) -> List[Dict[str, Any]]:
#         """
#         Get documents with temporal data within a specific date range.
#
#         Use this when:
#         - User specifies start and end dates
#         - Analyzing documents from a specific time period
#         - Questions like "Show me all invoices from Q1 2023"
#
#         Args:
#             query: DateRangeQuery with start_date, end_date, and optional limit
#
#         Returns:
#             List of temporal extraction records with document info and dates
#
#         Example queries:
#         - "Find all documents dated between 2023-01-01 and 2023-03-31"
#         - "Show me invoices from last quarter"
#         - "What documents have dates in August 2023?"
#         """
#         try:
#             return self.temporal_crud.get_by_date_range(
#                 start_date=query.start_date,
#                 end_date=query.end_date,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve documents by date range: {str(e)}"}]
#
#     weave.op()
#     async def get_documents_by_date_type(self, query: DateTypeQuery) -> List[Dict[str, Any]]:
#         """
#         Get documents by specific date type (invoice_date, due_date, etc.).
#
#         Use this when:
#         - User asks for specific type of dates
#         - Filtering by semantic date meaning
#         - Questions like "Show me all due dates" or "Find invoice dates"
#
#         Args:
#             query: DateTypeQuery with date_type and optional limit
#
#         Returns:
#             List of temporal extraction records of the specified type
#
#         Common date types:
#         - invoice_date: When invoice was issued
#         - due_date: When payment is due
#         - payment_date: When payment was made
#         - contract_start: Contract start date
#         - contract_end: Contract end date
#         - event_date: Event or meeting dates
#
#         Example queries:
#         - "Show me all invoice dates"
#         - "Find documents with due dates"
#         - "What are the contract start dates?"
#         """
#         try:
#             return self.temporal_crud.get_by_date_type(
#                 date_type=query.date_type,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve documents by date type: {str(e)}"}]
#
#     weave.op()
#     async def get_recent_temporal_data(self, query: RecentDataQuery) -> List[Dict[str, Any]]:
#         """
#         Get recent temporal extractions from the last N days.
#
#         Use this when:
#         - User asks about recent activity
#         - Time-based analysis of recent documents
#         - Questions like "What's been processed lately?"
#
#         Args:
#             query: RecentDataQuery with days and optional limit
#
#         Returns:
#             List of recent temporal extraction records
#
#         Example queries:
#         - "Show me documents processed in the last 7 days"
#         - "What temporal data was extracted recently?"
#         - "Find recent invoices and due dates"
#         """
#         try:
#             return self.temporal_crud.get_recent_temporal_data(
#                 days=query.days,
#                 limit=query.limit
#             )
#         except Exception as e:
#             return [{"error": f"Failed to retrieve recent temporal data: {str(e)}"}]
#
#     weave.op()
#     async def get_temporal_statistics(self) -> Dict[str, Any]:
#         """
#         Get comprehensive temporal data statistics.
#
#         Use this when:
#         - User wants overview of temporal data
#         - Statistical analysis of date extractions
#         - Questions like "How much temporal data do we have?"
#
#         Returns:
#             Dictionary with temporal statistics including:
#             - total_temporal_records: Total count of temporal extractions
#             - extraction_classes: Breakdown by extraction class
#             - date_types: Breakdown by date type in attributes
#             - generated_at: When statistics were generated
#
#         Example queries:
#         - "Give me stats on temporal data"
#         - "How many dates have been extracted?"
#         - "What types of dates are most common?"
#         """
#         try:
#             return self.temporal_crud.get_date_statistics()
#         except Exception as e:
#             return {"error": f"Failed to retrieve temporal statistics: {str(e)}"}
#
#
# # Create the pydantic-ai tools
# def create_temporal_tools() -> List[Tool]:
#     """
#     Create all temporal analysis tools for pydantic-ai agents.
#
#     Returns:
#         List of Tool objects for temporal data analysis
#     """
#     temporal_tool = TemporalAnalysisTool()
#
#     tools = [
#         Tool(
#             temporal_tool.get_documents_by_date_range,
#             name="get_documents_by_date_range",
#             description="""Get documents with dates within a specific date range. Use when user specifies start and end dates or asks about documents from a specific time period. Requires start_date and end_date in YYYY-MM-DD format."""
#         ),
#         Tool(
#             temporal_tool.get_documents_by_date_type,
#             name="get_documents_by_date_type",
#             description="""Get documents by specific date type (invoice_date, due_date, contract_start, etc.). Use when user asks for specific types of dates or wants to filter by semantic date meaning."""
#         ),
#         Tool(
#             temporal_tool.get_recent_temporal_data,
#             name="get_recent_temporal_data",
#             description="""Get recent temporal extractions from the last N days. Use when user asks about recent activity, latest documents, or time-based analysis of recent data."""
#         ),
#         Tool(
#             temporal_tool.get_temporal_statistics,
#             name="get_temporal_statistics",
#             description="""Get comprehensive statistics about temporal data including total records, extraction classes, and date type breakdowns. Use when user wants overview or statistical analysis of temporal data."""
#         )
#     ]
#
#     return tools
#
#
# # Export the tools for easy import
# temporal_analysis_tools = create_temporal_tools()