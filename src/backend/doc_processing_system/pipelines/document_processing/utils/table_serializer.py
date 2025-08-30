"""
TableSerializer - Advanced table serialization strategies for document processing.
Handles conversion of Docling table objects to various formats.
"""

import logging
from typing import Dict, Any

from .serialization_strategies import SerializationStrategy


class TableSerializer:
    """Advanced table serialization with multiple strategy support."""
    
    def __init__(self, strategy: SerializationStrategy = SerializationStrategy.STRUCTURED):
        """Initialize table serializer with specified strategy.
        
        Args:
            strategy: Serialization strategy to use
        """
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
    
    def serialize_table(self, table, table_id: int) -> Dict[str, Any]:
        """Serialize table using configured strategy.
        
        Args:
            table: Docling table object
            table_id: Unique table identifier
            
        Returns:
            Dict containing serialized table data
        """
        base_data = {
            "table_id": table_id,
            "position": getattr(table, 'prov', []),
            "rows": getattr(table, 'num_rows', 0),
            "columns": getattr(table, 'num_cols', 0),
            "strategy": self.strategy.value
        }
        
        if self.strategy == SerializationStrategy.STRUCTURED:
            base_data.update(self._serialize_structured(table))
        elif self.strategy == SerializationStrategy.MARKDOWN:
            base_data.update(self._serialize_markdown(table))
        elif self.strategy == SerializationStrategy.JSON:
            base_data.update(self._serialize_json(table))
        elif self.strategy == SerializationStrategy.DETAILED:
            base_data.update(self._serialize_detailed(table))
        else:  # DEFAULT
            base_data["data"] = self._table_to_dict(table)
        
        return base_data
    
    def _table_to_dict(self, table) -> Dict[str, Any]:
        """Convert table object to dictionary representation."""
        try:
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                return df.to_dict('records')
            else:
                return {"raw": str(table)}
        except Exception:
            return {"raw": str(table)}
    
    def _serialize_structured(self, table) -> Dict[str, Any]:
        """Structured table serialization with headers and data separation."""
        try:
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                return {
                    "headers": df.columns.tolist(),
                    "data_rows": df.values.tolist(),
                    "data_dict": df.to_dict('records'),
                    "table_type": "structured_dataframe"
                }
            else:
                return {
                    "raw_content": str(table),
                    "table_type": "raw_structured"
                }
        except Exception as e:
            return {
                "error": str(e),
                "raw_content": str(table),
                "table_type": "error_fallback"
            }
    
    def _serialize_markdown(self, table) -> Dict[str, Any]:
        """Markdown table serialization."""
        try:
            if hasattr(table, 'export_to_markdown'):
                markdown_table = table.export_to_markdown()
            elif hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                markdown_table = df.to_markdown(index=False)
            else:
                markdown_table = f"```\n{str(table)}\n```"
            
            return {
                "markdown_content": markdown_table,
                "table_type": "markdown_formatted",
                "line_count": len(markdown_table.split('\n'))
            }
        except Exception as e:
            return {
                "error": str(e),
                "markdown_content": f"```\n{str(table)}\n```",
                "table_type": "markdown_error_fallback"
            }
    
    def _serialize_json(self, table) -> Dict[str, Any]:
        """JSON table serialization with metadata."""
        try:
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                json_data = {
                    "table_data": df.to_dict('records'),
                    "columns": df.columns.tolist(),
                    "shape": df.shape,
                    "dtypes": df.dtypes.to_dict() if hasattr(df.dtypes, 'to_dict') else {}
                }
            else:
                json_data = {"raw_content": str(table)}
            
            return {
                "json_representation": json_data,
                "table_type": "json_structured",
                "serializable": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "json_representation": {"raw_content": str(table)},
                "table_type": "json_error_fallback",
                "serializable": False
            }
    
    def _serialize_detailed(self, table) -> Dict[str, Any]:
        """Detailed table serialization with comprehensive metadata."""
        try:
            result = {
                "table_type": "detailed_analysis",
                "raw_content": str(table)
            }
            
            # Try to get structured data
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                result.update({
                    "structured_data": {
                        "headers": df.columns.tolist(),
                        "data_rows": df.values.tolist(),
                        "shape": df.shape,
                        "column_types": df.dtypes.to_dict() if hasattr(df.dtypes, 'to_dict') else {}
                    },
                    "markdown_representation": df.to_markdown(index=False),
                    "data_summary": {
                        "total_cells": df.size,
                        "non_null_cells": df.count().sum() if hasattr(df.count(), 'sum') else 0,
                        "column_count": len(df.columns),
                        "row_count": len(df)
                    }
                })
            
            # Add any available attributes
            for attr in ['caption', 'title', 'bbox', 'prov']:
                if hasattr(table, attr):
                    result[attr] = getattr(table, attr)
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "table_type": "detailed_error_fallback",
                "raw_content": str(table)
            }
