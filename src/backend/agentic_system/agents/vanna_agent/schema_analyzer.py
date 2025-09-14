"""
Schema analyzer for automatically extracting and training on database schemas
"""

import pandas as pd
from typing import Dict, List
import time
import logging
from dotenv import load_dotenv

load_dotenv()


class SchemaAnalyzer:
    """Analyzes database schemas and generates training data"""

    def __init__(self, db_manager, vanna_instance):
        """Initialize schema analyzer"""
        self.db_manager = db_manager
        self.vn = vanna_instance
        self.db_details = db_manager.get_connection_details()

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def auto_extract_schema(self) -> pd.DataFrame:
        """Intelligently extract schema based on database type"""
        db_type = self.db_details['type']

        # Database-specific schema queries
        schema_queries = {
            'postgresql': """
                SELECT
                    table_schema,
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY table_schema, table_name, ordinal_position
            """,
            'mysql': """
                SELECT
                    table_schema,
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    column_key,
                    extra
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                ORDER BY table_schema, table_name, ordinal_position
            """,
            'sqlite': """
                SELECT
                    '' as table_schema,
                    m.name as table_name,
                    p.name as column_name,
                    p.type as data_type,
                    CASE WHEN p.[notnull] = 0 THEN 'YES' ELSE 'NO' END as is_nullable,
                    p.dflt_value as column_default,
                    NULL as character_maximum_length,
                    NULL as numeric_precision,
                    NULL as numeric_scale
                FROM sqlite_master m
                LEFT OUTER JOIN pragma_table_info(m.name) p ON m.name != p.name
                WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
                ORDER BY m.name, p.cid
            """
        }

        query = schema_queries.get(db_type, schema_queries['postgresql'])
        return self.db_manager.run_sql(query)

    def extract_relationships(self) -> List[Dict]:
        """Extract foreign key relationships"""
        try:
            relationships = []
            for table_name in self.db_details['tables']:
                fks = self.db_manager.inspector.get_foreign_keys(table_name)
                for fk in fks:
                    relationships.append({
                        'source_table': table_name,
                        'source_columns': fk['constrained_columns'],
                        'target_table': fk['referred_table'],
                        'target_columns': fk['referred_columns']
                    })
            return relationships
        except Exception as e:
            self.logger.warning(f"Could not extract relationships: {str(e)}")
            return []

    def generate_sample_data_insights(self, table_name: str, limit: int = 5) -> str:
        """Generate insights from sample data"""
        try:
            sample_df = self.db_manager.run_sql(f"SELECT * FROM {table_name} LIMIT {limit}")
            insights = [
                f"Table {table_name} has {len(sample_df.columns)} columns",
                f"Sample row count: {len(sample_df)}",
                f"Columns: {', '.join(sample_df.columns.tolist())}"
            ]

            # Add data type insights
            for col in sample_df.columns:
                if sample_df[col].dtype in ['int64', 'float64']:
                    insights.append(
                        f"{col} contains numeric data (range: {sample_df[col].min()} to {sample_df[col].max()})")
                elif sample_df[col].dtype == 'object':
                    unique_count = sample_df[col].nunique()
                    insights.append(f"{col} contains text data ({unique_count} unique values in sample)")

            return "; ".join(insights)
        except Exception as e:
            return f"Could not analyze table {table_name}: {str(e)}"

    def run_advanced_training(self) -> Dict:
        """Comprehensive automatic training process"""
        self.logger.info("Starting Advanced Auto-Training...")

        # Step 1: Extract and train on schema
        self.logger.info("Extracting database schema...")
        schema_df = self.auto_extract_schema()

        # Generate intelligent training plan
        training_plan = self.vn.get_training_plan_generic(schema_df)
        self.logger.info(f"Generated training plan with {len(training_plan)} items")

        # Execute training plan in batches for better performance
        batch_size = 10
        for i in range(0, len(training_plan), batch_size):
            batch = training_plan[i:i + batch_size]
            self.logger.info(f"Training batch {i // batch_size + 1}/{(len(training_plan) + batch_size - 1) // batch_size}")
            self.vn.train(plan=batch)
            time.sleep(0.5)  # Rate limiting

        # Step 2: Extract and train on relationships
        self.logger.info("Analyzing table relationships...")
        relationships = self.extract_relationships()
        for rel in relationships:
            relationship_ddl = f"""
            -- Relationship: {rel['source_table']} -> {rel['target_table']}
            ALTER TABLE {rel['source_table']}
            ADD FOREIGN KEY ({', '.join(rel['source_columns'])})
            REFERENCES {rel['target_table']}({', '.join(rel['target_columns'])})
            """
            self.vn.train(ddl=relationship_ddl)

        # Step 3: Generate business context from sample data
        self.logger.info("Generating business insights...")
        for table in self.db_details['tables'][:10]:  # Limit to first 10 tables
            try:
                insights = self.generate_sample_data_insights(table)
                self.vn.train(documentation=f"Table {table}: {insights}")
            except Exception as e:
                self.logger.warning(f"Could not analyze table {table}: {str(e)}")

        # Step 4: Add common business patterns
        business_patterns = [
            "Active records typically have status = 'active' or deleted_at IS NULL",
            "Timestamps like created_at, updated_at track record lifecycle",
            "Foreign key columns typically end with '_id'",
            "Aggregations often use SUM, COUNT, AVG for reporting",
            "Date ranges commonly use BETWEEN for filtering"
        ]

        for pattern in business_patterns:
            self.vn.train(documentation=pattern)

        self.logger.info("Advanced auto-training completed!")

        # Performance summary
        training_data = self.vn.get_training_data()
        summary = {
            'total_training_items': len(training_data),
            'tables_analyzed': len(self.db_details['tables']),
            'relationships_found': len(relationships),
            'business_patterns_added': len(business_patterns)
        }

        self.logger.info(f"Training Summary: {summary}")
        return summary