"""
Document Analysis Agent schema for structured responses
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DocumentAnalysisResponse(BaseModel):
    """
    Structured response from document analysis agent.
    """
    analysis: str = Field(description="Natural language analysis of the query results")
    data_summary: Dict[str, Any] = Field(description="Summary of key findings from the data")
    recommendations: Optional[List[str]] = Field(description="Action items or recommendations based on findings")
    metadata: Dict[str, Any] = Field(description="Query metadata and processing information")


class QueryContext(BaseModel):
    """
    Context information for document analysis queries.
    """
    query: str = Field(description="The user's natural language query")
    query_type: str = Field(description="Categorized type of query (temporal, financial, product, general)")
    requires_tools: List[str] = Field(description="List of tools that should be used for this query")