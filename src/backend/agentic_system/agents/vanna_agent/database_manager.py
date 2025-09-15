"""
Database manager for handling database connections and SQL execution
"""
import os
import time
import logging
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    """Handles database connections and SQL execution with performance tracking"""

    def __init__(self, connection_string: str):
        """Initialize database manager with connection string"""
        self.engine = create_engine(connection_string, pool_pre_ping=True)
        self.inspector = inspect(self.engine)

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.performance_metrics = []

    def get_connection_details(self) -> Dict:
        """Auto-detect database type and capabilities"""
        db_type = self.engine.dialect.name
        version = (self.engine.dialect.server_version_info
                  if hasattr(self.engine.dialect, 'server_version_info')
                  else 'Unknown')

        return {
            'type': db_type,
            'version': version,
            'tables': self.inspector.get_table_names(),
            'schemas': (self.inspector.get_schema_names()
                       if hasattr(self.inspector, 'get_schema_names')
                       else ['public'])
        }

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Enhanced SQL execution with error handling and performance tracking"""
        start_time = time.time()

        try:
            with self.engine.connect() as conn:
                result = pd.read_sql_query(text(sql), conn)
                execution_time = time.time() - start_time

                # Track performance metrics
                self.performance_metrics.append({
                    'sql': sql[:100] + '...' if len(sql) > 100 else sql,
                    'execution_time': execution_time,
                    'rows_returned': len(result),
                    'timestamp': time.time()
                })

                self.logger.info(f"SQL executed successfully: {len(result)} rows, {execution_time:.3f}s")
                return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"SQL execution failed after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"SQL: {sql}")
            raise

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                self.logger.info("Database connection successful")
                return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False

    def get_performance_summary(self) -> Dict:
        """Get performance metrics summary"""
        if not self.performance_metrics:
            return {"message": "No performance metrics available"}

        df_metrics = pd.DataFrame(self.performance_metrics)
        return {
            'total_queries': len(df_metrics),
            'avg_execution_time': df_metrics['execution_time'].mean(),
            'total_rows_processed': df_metrics['rows_returned'].sum(),
            'fastest_query': df_metrics['execution_time'].min(),
            'slowest_query': df_metrics['execution_time'].max()
        }


if __name__ == "__main__":
    dbm = DatabaseManager(connection_string=os.getenv("POSTGRES_DSN"))
    print(
        dbm.get_connection_details()
    )
    print(dbm.inspector.get_table_names())
