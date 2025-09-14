# Enhanced Installation with all dependencies
import os
import pandas as pd
from vanna.chromadb import ChromaDB_VectorStore
from vanna.google import GoogleGeminiChat
from sqlalchemy import create_engine, text, inspect
import logging
from typing import Dict, List, Optional
import time


class AdvancedVanna(ChromaDB_VectorStore, GoogleGeminiChat):
    def __init__(self, config: Dict = None):
        # Optimal ChromaDB Configuration
        chroma_config = {
            'path': './vanna_chromadb',  # Persistent storage
            'collection_name': f'vanna_training_{int(time.time())}',  # Unique collection
            'embedding_function': 'all-MiniLM-L6-v2',  # Fast, accurate embeddings
        }

        # Advanced Gemini Configuration
        gemini_config = {
            'api_key': os.getenv('GEMINI_API_KEY'),
            'model': 'gemini-1.5-pro',  # Most capable model
            'temperature': 0.1,  # Low for consistent SQL generation
            'max_tokens': 8192,  # Sufficient for complex queries
            'safety_settings': {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_MEDIUM_AND_ABOVE'
            }
        }

        ChromaDB_VectorStore.__init__(self, config=chroma_config)
        GoogleGeminiChat.__init__(self, config=gemini_config)

        # Performance tracking
        self.query_cache = {}
        self.performance_metrics = []

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)


# Initialize with optimal settings
vn = AdvancedVanna()


# Advanced Database Connection with Auto-Detection
class DatabaseManager:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string, pool_pre_ping=True)
        self.inspector = inspect(self.engine)

    def get_connection_details(self):
        """Auto-detect database type and capabilities"""
        db_type = self.engine.dialect.name
        version = self.engine.dialect.server_version_info if hasattr(self.engine.dialect,
                                                                     'server_version_info') else 'Unknown'

        return {
            'type': db_type,
            'version': version,
            'tables': self.inspector.get_table_names(),
            'schemas': self.inspector.get_schema_names() if hasattr(self.inspector, 'get_schema_names') else ['public']
        }

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Enhanced SQL execution with error handling"""
        start_time = time.time()
        try:
            with self.engine.connect() as conn:
                result = pd.read_sql_query(text(sql), conn)
                execution_time = time.time() - start_time
                vn.performance_metrics.append({
                    'sql': sql[:100] + '...' if len(sql) > 100 else sql,
                    'execution_time': execution_time,
                    'rows_returned': len(result),
                    'timestamp': time.time()
                })
                return result
        except Exception as e:
            vn.logger.error(f"SQL execution failed: {str(e)}")
            raise


# Database connection setup (replace with your details)
CONNECTION_STRING = "postgresql://user:password@localhost:5432/database"
# CONNECTION_STRING = "mysql+pymysql://user:password@localhost:3306/database"
# CONNECTION_STRING = "mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+17+for+SQL+Server"

db_manager = DatabaseManager(CONNECTION_STRING)
vn.run_sql = db_manager.run_sql
vn.run_sql_is_set = True


# Advanced Auto-Schema Training
class SchemaAnalyzer:
    def __init__(self, db_manager: DatabaseManager, vanna_instance):
        self.db_manager = db_manager
        self.vn = vanna_instance
        self.db_details = db_manager.get_connection_details()

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

        query = schema_queries.get(db_type, schema_queries['postgresql'])  # Default to PostgreSQL
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
            self.vn.logger.warning(f"Could not extract relationships: {str(e)}")
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


# Execute Advanced Auto-Training
def advanced_auto_training():
    """Comprehensive automatic training process"""
    print("🚀 Starting Advanced Auto-Training...")

    analyzer = SchemaAnalyzer(db_manager, vn)

    # Step 1: Extract and train on schema
    print("📊 Extracting database schema...")
    schema_df = analyzer.auto_extract_schema()

    # Generate intelligent training plan
    training_plan = vn.get_training_plan_generic(schema_df)
    print(f"📋 Generated training plan with {len(training_plan)} items")

    # Execute training plan in batches for better performance
    batch_size = 10
    for i in range(0, len(training_plan), batch_size):
        batch = training_plan[i:i + batch_size]
        print(f"🎯 Training batch {i // batch_size + 1}/{(len(training_plan) + batch_size - 1) // batch_size}")
        vn.train(plan=batch)
        time.sleep(0.5)  # Rate limiting

    # Step 2: Extract and train on relationships
    print("🔗 Analyzing table relationships...")
    relationships = analyzer.extract_relationships()
    for rel in relationships:
        relationship_ddl = f"""
        -- Relationship: {rel['source_table']} -> {rel['target_table']}
        ALTER TABLE {rel['source_table']} 
        ADD FOREIGN KEY ({', '.join(rel['source_columns'])}) 
        REFERENCES {rel['target_table']}({', '.join(rel['target_columns'])})
        """
        vn.train(ddl=relationship_ddl)

    # Step 3: Generate business context from sample data
    print("💡 Generating business insights...")
    for table in analyzer.db_details['tables'][:10]:  # Limit to first 10 tables
        try:
            insights = analyzer.generate_sample_data_insights(table)
            vn.train(documentation=f"Table {table}: {insights}")
        except Exception as e:
            print(f"⚠️ Could not analyze table {table}: {str(e)}")

    # Step 4: Add common business patterns
    business_patterns = [
        "Active records typically have status = 'active' or deleted_at IS NULL",
        "Timestamps like created_at, updated_at track record lifecycle",
        "Foreign key columns typically end with '_id'",
        "Aggregations often use SUM, COUNT, AVG for reporting",
        "Date ranges commonly use BETWEEN for filtering"
    ]

    for pattern in business_patterns:
        vn.train(documentation=pattern)

    print("✅ Advanced auto-training completed!")

    # Performance summary
    training_data = vn.get_training_data()
    print(f"📈 Training Summary:")
    print(f"   - Total training items: {len(training_data)}")
    print(f"   - Tables analyzed: {len(analyzer.db_details['tables'])}")
    print(f"   - Relationships found: {len(relationships)}")


# Execute the advanced training
advanced_auto_training()


# Advanced Query Interface with Caching
class OptimizedQueryInterface:
    def __init__(self, vanna_instance):
        self.vn = vanna_instance

    def smart_ask(self, question: str, use_cache: bool = True) -> Dict:
        """Enhanced ask with caching and performance metrics"""
        question_hash = hash(question)

        # Check cache first
        if use_cache and question_hash in self.vn.query_cache:
            print("🚀 Retrieved from cache")
            return self.vn.query_cache[question_hash]

        start_time = time.time()

        try:
            # Generate SQL with explanation
            sql = self.vn.generate_sql(question)

            # Execute and measure performance
            result_df = self.vn.run_sql(sql)

            execution_time = time.time() - start_time

            response = {
                'question': question,
                'sql': sql,
                'result': result_df,
                'execution_time': execution_time,
                'row_count': len(result_df),
                'success': True
            }

            # Cache successful results
            if use_cache:
                self.vn.query_cache[question_hash] = response

            return response

        except Exception as e:
            return {
                'question': question,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'success': False
            }


# Initialize optimized interface
query_interface = OptimizedQueryInterface(vn)

# Usage Examples
print("\n🎯 Testing Advanced Configuration:")

# Test queries
test_questions = [
    "How many customers do we have?",
    "What are the top 5 products by sales?",
    "Show me monthly revenue trends",
    "Which customers haven't ordered in the last 30 days?"
]

for question in test_questions:
    print(f"\n❓ Question: {question}")
    response = query_interface.smart_ask(question)

    if response['success']:
        print(f"✅ SQL: {response['sql']}")
        print(f"📊 Rows returned: {response['row_count']}")
        print(f"⚡ Execution time: {response['execution_time']:.2f}s")
    else:
        print(f"❌ Error: {response['error']}")


# Performance Analytics
def show_performance_analytics():
    """Display performance insights"""
    if vn.performance_metrics:
        df_metrics = pd.DataFrame(vn.performance_metrics)
        print(f"\n📈 Performance Analytics:")
        print(f"   - Total queries: {len(df_metrics)}")
        print(f"   - Average execution time: {df_metrics['execution_time'].mean():.3f}s")
        print(f"   - Total rows processed: {df_metrics['rows_returned'].sum():,}")
        print(f"   - Cache hit rate: {len(vn.query_cache) / len(df_metrics) * 100:.1f}%")


show_performance_analytics()

# Launch Enhanced Web Interface
from vanna.flask import VannaFlaskApp

print("\n🌐 Launching optimized web interface...")
app = VannaFlaskApp(vn, allow_llm_to_see_data=True)
app.run(host='0.0.0.0', port=8084, debug=False)
