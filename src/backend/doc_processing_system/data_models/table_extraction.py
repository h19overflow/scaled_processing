"""
Table extraction data models for configurable field mapping.
Contains models for table field specifications and extraction configuration.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class TableFieldMapping(BaseModel):
    """Model for individual table field mapping configuration."""
    field_name: str
    english_translation: str
    table_id: int
    extraction_path: str
    example_value: str
    field_type: str = "string"
    is_required: bool = False

    def extract_value(self, tables_data: List[Dict[str, Any]]) -> Any:
        """Extract value from tables data using direct indexing path."""
        try:
            # Find the target table
            target_table = None
            for table in tables_data:
                if table.get("table_id") == self.table_id:
                    target_table = table
                    break

            if not target_table:
                return None

            # Get table data
            table_data = target_table.get("data", [])
            if not table_data:
                return None

            # Use direct path evaluation (e.g., "data[0]['Amaun (RM)']")
            value = self._extract_by_direct_path(table_data, self.extraction_path)
            return self._convert_type(value)

        except Exception:
            return None

    def _extract_by_direct_path(self, data: List[Dict], path: str) -> Any:
        """Extract value using direct indexing path like 'data[0]['field']'."""
        try:
            # Handle direct index access patterns
            if path.startswith("data["):
                # Parse path like "data[0]['Amaun (RM)']" or "data[4].field"

                # Find the index part
                bracket_end = path.find("]")
                if bracket_end == -1:
                    return None

                index_str = path[5:bracket_end]  # Extract index from "data[X]"
                index = int(index_str)

                # Check bounds
                if index < 0 or index >= len(data):
                    return None

                # Get the row data
                row_data = data[index]

                # Handle field access after the index
                remaining_path = path[bracket_end + 1:]

                if remaining_path.startswith("['") and remaining_path.endswith("']"):
                    # Handle "data[0]['field name']" format
                    field_name = remaining_path[2:-2]  # Remove [' and ']
                    return row_data.get(field_name)
                elif remaining_path.startswith("."):
                    # Handle "data[0].field" format
                    field_name = remaining_path[1:]  # Remove the dot
                    return row_data.get(field_name)
                else:
                    # Just return the row if no field specified
                    return row_data

            # Handle simple field access for backward compatibility
            elif path in data[0] if data else False:
                return data[0].get(path)

            return None

        except (ValueError, IndexError, KeyError, TypeError):
            return None

    def _convert_type(self, value: Any) -> Any:
        """Convert value to the specified field type."""
        if value is None:
            return None

        str_value = str(value).strip()

        if self.field_type == "float":
            try:
                # Handle formatted numbers like "950.00kW"
                clean_value = ''.join(c for c in str_value if c.isdigit() or c == '.')
                return float(clean_value) if clean_value else None
            except ValueError:
                return None
        elif self.field_type == "int":
            try:
                clean_value = ''.join(c for c in str_value if c.isdigit())
                return int(clean_value) if clean_value else None
            except ValueError:
                return None

        return str_value


class TableExtractionConfig(BaseModel):
    """Model for table extraction configuration."""
    document_type: str
    description: str
    field_mappings: List[TableFieldMapping]
    created_at: Optional[datetime] = None

    def get_field_mapping(self, field_name: str) -> Optional[TableFieldMapping]:
        """Get field mapping by name."""
        for mapping in self.field_mappings:
            if mapping.field_name == field_name:
                return mapping
        return None

    def extract_all_fields(self, tables_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all configured fields from tables data."""
        results = {}

        for mapping in self.field_mappings:
            value = mapping.extract_value(tables_data)
            if value is not None:
                results[mapping.field_name] = {
                    "value": value,
                    "english_translation": mapping.english_translation,
                    "table_id": mapping.table_id,
                    "field_type": mapping.field_type
                }

        return results

    def get_required_fields(self) -> List[str]:
        """Get list of required field names."""
        return [mapping.field_name for mapping in self.field_mappings if mapping.is_required]


class TableExtractionResult(BaseModel):
    """Model for table extraction results."""
    document_id: str
    document_name: str
    table_extractions: Dict[str, Any]
    extraction_config: str
    tables_count: int
    timestamp: Optional[datetime] = None

    def to_extraction_results(self) -> List[Dict[str, Any]]:
        """Convert to list of ExtractionResult-compatible dictionaries."""
        results = []

        for field_name, field_data in self.table_extractions.items():
            result = {
                "extraction_class": "table_field",
                "extraction_text": str(field_data.get("value", "")),
                "attributes": {
                    "field_name": field_name,
                    "english_translation": field_data.get("english_translation", ""),
                    "table_id": field_data.get("table_id", 0),
                    "field_type": field_data.get("field_type", "string"),
                    "extraction_config": self.extraction_config,
                    "source": "table_extraction"
                },
                "alignment_status": "match_exact",
                "extraction_index": len(results),
                "group_index": 0,
                "description": f"Table field: {field_name}",
                "char_start_pos": 0,
                "char_end_pos": len(str(field_data.get("value", "")))
            }
            results.append(result)

        return results