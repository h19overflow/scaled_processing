"""
Schema analyzer for automatically extracting and training on database schemas
"""

import pandas as pd
from typing import Dict, List
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
        """Intelligently extract schema based on a database type"""
        db_type = self.db_details['type']

        # Database-specific schema queries
        schema_queries = {
            'postgresql': """
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY table_name, ordinal_position
            
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

        # Generate manual training data from schema
        self.logger.info(f"Schema dataframe columns: {list(schema_df.columns)}")
        self.logger.info(f"Schema dataframe shape: {schema_df.shape}")

        # Create manual training data from schema
        training_count = 0
        for table_name in schema_df['table_name'].unique():
            table_columns = schema_df[schema_df['table_name'] == table_name]

            # Create DDL statement for the table
            ddl = f"CREATE TABLE {table_name} ("
            column_definitions = []

            for _, row in table_columns.iterrows():
                col_def = f"{row['column_name']} {row['data_type']}"
                if row['is_nullable'] == 'NO':
                    col_def += " NOT NULL"
                column_definitions.append(col_def)

            ddl += ", ".join(column_definitions) + ");"

            # Train on DDL
            self.vn.train(ddl=ddl)
            training_count += 1

            # Add documentation about the table
            doc = f"Table {table_name} contains columns: {', '.join(table_columns['column_name'].tolist())}"
            self.vn.train(documentation=doc)
            training_count += 1

        self.logger.info(f"Created {training_count} manual training items from schema")

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