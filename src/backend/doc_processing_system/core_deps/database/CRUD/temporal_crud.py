"""
Temporal CRUD operations for agentic system.
Provides minimal-input queries for temporal data analysis with maximum security.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy import and_, or_, func, cast, Date, text

from .base_repository import BaseRepository
from ..models import StructuredDocumentModel
import weave
weave.init(project_name="scaled_processing")

class TemporalCRUD(BaseRepository):
    """CRUD operations for temporal data analysis with minimal input requirements."""
    @weave.op()
    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get documents with temporal data within date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum records to return (default 100, max 1000)

        Returns:
            List of temporal extraction records
        """
        try:
            # Input validation and sanitization
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            limit = min(max(1, limit), 1000)  # Clamp between 1-1000

            with self.connection_manager.get_session() as session:
                # Use text SQL for JSON queries
                query = text("""
                    SELECT document_id, document_name, extraction_class, extraction_text,
                           attributes, created_at
                    FROM structured_documents
                    WHERE attributes->>'iso_date' IS NOT NULL
                    AND CAST(attributes->>'iso_date' AS DATE) BETWEEN :start_date AND :end_date
                    ORDER BY CAST(attributes->>'iso_date' AS DATE) DESC
                    LIMIT :limit
                """)

                result = session.execute(query, {
                    'start_date': start_dt,
                    'end_date': end_dt,
                    'limit': limit
                })

                temporal_data = []
                for row in result:
                    import json
                    # Handle attributes - could be dict or string
                    if isinstance(row.attributes, dict):
                        attrs = row.attributes
                    elif isinstance(row.attributes, str):
                        attrs = json.loads(row.attributes)
                    else:
                        attrs = {}

                    temporal_data.append({
                        'document_id': str(row.document_id),
                        'document_name': row.document_name,
                        'extraction_class': row.extraction_class,
                        'extraction_text': row.extraction_text,
                        'iso_date': attrs.get('iso_date'),
                        'date_type': attrs.get('type', 'unknown'),
                        'created_at': row.created_at.isoformat()
                    })

                self._log_operation("Retrieved temporal data by date range",
                                  details=f"range: {start_date} to {end_date}, count: {len(temporal_data)}")
                return temporal_data

        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            raise ValueError("Date must be in YYYY-MM-DD format")
        except Exception as e:
            self.logger.error(f"Failed to get temporal data by date range: {e}")
            raise

    @weave.op()
    def get_by_date_type(self, date_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get documents by specific date type.

        Args:
            date_type: Type of date ('invoice_date', 'due_date', etc.)
            limit: Maximum records to return (default 100, max 1000)

        Returns:
            List of temporal extraction records of specified type
        """
        try:
            # Input sanitization
            date_type = date_type.lower().strip()
            limit = min(max(1, limit), 1000)

            with self.connection_manager.get_session() as session:
                query = text("""
                    SELECT document_id, document_name, extraction_text, attributes, created_at
                    FROM structured_documents
                    WHERE extraction_class = :date_type
                    AND attributes->>'iso_date' IS NOT NULL
                    ORDER BY CAST(attributes->>'iso_date' AS DATE) DESC
                    LIMIT :limit
                """)

                result = session.execute(query, {
                    'date_type': date_type,
                    'limit': limit
                })

                temporal_data = []
                for row in result:
                    import json
                    # Handle attributes - could be dict or string
                    if isinstance(row.attributes, dict):
                        attrs = row.attributes
                    elif isinstance(row.attributes, str):
                        attrs = json.loads(row.attributes)
                    else:
                        attrs = {}

                    temporal_data.append({
                        'document_id': str(row.document_id),
                        'document_name': row.document_name,
                        'extraction_text': row.extraction_text,
                        'iso_date': attrs.get('iso_date'),
                        'date_type': attrs.get('type', 'unknown'),
                        'created_at': row.created_at.isoformat()
                    })

                self._log_operation("Retrieved temporal data by date type",
                                  details=f"type: {date_type}, count: {len(temporal_data)}")
                return temporal_data

        except Exception as e:
            self.logger.error(f"Failed to get temporal data by date type: {e}")
            raise

    @weave.op()
    def get_recent_temporal_data(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent temporal extractions from last N days.

        Args:
            days: Number of recent days to query (max 365)
            limit: Maximum records to return (default 50, max 500)

        Returns:
            List of recent temporal extraction records
        """
        try:
            # Input validation
            days = min(max(1, days), 365)  # Clamp between 1-365 days
            limit = min(max(1, limit), 500)

            with self.connection_manager.get_session() as session:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days)

                query = text("""
                    SELECT document_id, document_name, extraction_class, extraction_text,
                           attributes, created_at
                    FROM structured_documents
                    WHERE attributes->>'iso_date' IS NOT NULL
                    AND created_at >= :cutoff_date
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)

                result = session.execute(query, {
                    'cutoff_date': cutoff_date,
                    'limit': limit
                })

                temporal_data = []
                for row in result:
                    import json
                    # Handle attributes - could be dict or string
                    if isinstance(row.attributes, dict):
                        attrs = row.attributes
                    elif isinstance(row.attributes, str):
                        attrs = json.loads(row.attributes)
                    else:
                        attrs = {}

                    temporal_data.append({
                        'document_id': str(row.document_id),
                        'document_name': row.document_name,
                        'extraction_class': row.extraction_class,
                        'extraction_text': row.extraction_text,
                        'iso_date': attrs.get('iso_date'),
                        'date_type': attrs.get('type', 'unknown'),
                        'created_at': row.created_at.isoformat()
                    })

                self._log_operation("Retrieved recent temporal data",
                                  details=f"days: {days}, count: {len(temporal_data)}")
                return temporal_data

        except Exception as e:
            self.logger.error(f"Failed to get recent temporal data: {e}")
            raise

    @weave.op()
    def get_date_statistics(self) -> Dict[str, Any]:
        """Get temporal data statistics with minimal computation.

        Returns:
            Dictionary with temporal statistics
        """
        try:
            with self.connection_manager.get_session() as session:
                # Count by extraction class
                class_query = text("""
                    SELECT extraction_class, COUNT(*)
                    FROM structured_documents
                    WHERE attributes->>'iso_date' IS NOT NULL
                    GROUP BY extraction_class
                """)
                class_result = session.execute(class_query)
                class_counts = dict(class_result.fetchall())

                # Count by date type in attributes
                type_query = text("""
                    SELECT attributes->>'type' as date_type, COUNT(*)
                    FROM structured_documents
                    WHERE attributes->>'iso_date' IS NOT NULL
                    AND attributes->>'type' IS NOT NULL
                    GROUP BY attributes->>'type'
                """)
                type_result = session.execute(type_query)
                type_counts = dict(type_result.fetchall())

                # Total count
                total_query = text("""
                    SELECT COUNT(*)
                    FROM structured_documents
                    WHERE attributes->>'iso_date' IS NOT NULL
                """)
                total_result = session.execute(total_query)
                total_count = total_result.scalar()

                stats = {
                    'total_temporal_records': total_count,
                    'extraction_classes': class_counts,
                    'date_types': type_counts,
                    'generated_at': datetime.now().isoformat()
                }

                self._log_operation("Generated temporal statistics",
                                  details=f"total_records: {total_count}")
                return stats

        except Exception as e:
            self.logger.error(f"Failed to get temporal statistics: {e}")
            raise

    # HELPER FUNCTIONS
    def _validate_date_format(self, date_string: str) -> bool:
        """Validate date string format."""
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            return False


def demo_temporal_crud():
    """Demo function showing minimal input temporal queries."""
    from ..connection_manager import ConnectionManager

    print("🕐 TEMPORAL CRUD DEMO")
    print("=" * 50)

    try:
        # Initialize
        connection_manager = ConnectionManager()
        temporal_crud = TemporalCRUD(connection_manager)

        print("1. 📊 Getting Temporal Statistics...")
        stats = temporal_crud.get_date_statistics()
        print(f"   Total temporal records: {stats['total_temporal_records']}")
        print(f"   Extraction classes: {stats['extraction_classes']}")
        print(f"   Date types: {stats['date_types']}")
        print()

        print("2. 📅 Getting Recent Temporal Data (Last 30 days)...")
        recent_data = temporal_crud.get_recent_temporal_data(days=30, limit=5)
        for i, record in enumerate(recent_data[:3], 1):
            print(f"   Record {i}: {record['document_name']} - {record['iso_date']} ({record['extraction_class']})")
        print()

        print("3. 🗓️ Getting Invoice Dates...")
        invoice_dates = temporal_crud.get_by_date_type('invoice_date', limit=3)
        for i, record in enumerate(invoice_dates, 1):
            print(f"   Invoice {i}: {record['document_name']} - {record['iso_date']} - {record['extraction_text']}")
        print()

        print("4. 📆 Getting Date Range (2023-08-01 to 2023-12-31)...")
        range_data = temporal_crud.get_by_date_range('2023-08-01', '2023-12-31', limit=3)
        for i, record in enumerate(range_data, 1):
            print(f"   Document {i}: {record['document_name']} - {record['iso_date']} ({record['date_type']})")
        print()

        print("✅ Demo completed successfully!")
        print("🔒 Security: All inputs validated and sanitized")
        print("⚡ Performance: Minimal data returned with limits")

    except Exception as e:
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    demo_temporal_crud()