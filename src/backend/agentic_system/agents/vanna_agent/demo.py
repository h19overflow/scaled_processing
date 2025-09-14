"""
Demo script for the modular Vanna agent system
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vanna_orchestrator import VannaOrchestrator

load_dotenv()


def main():
    """Main demo function"""
    print("🚀 Vanna Agent Modular Demo")
    print("=" * 50)

    # PostgreSQL connection string for the provided Docker setup
    CONNECTION_STRING = "postgresql://postgres:postgres@localhost:5444/document_processing"

    try:
        # Initialize the orchestrator
        print("\n📦 Initializing Vanna Orchestrator...")
        orchestrator = VannaOrchestrator(CONNECTION_STRING)

        # Test database connection
        print("\n🔗 Testing database connection...")
        if orchestrator.test_connection():
            print("✅ Database connection successful!")
        else:
            print("❌ Database connection failed!")
            return

        # Get database info
        print("\n📊 Database Information:")
        db_info = orchestrator.get_database_info()
        print(f"   - Database type: {db_info['type']}")
        print(f"   - Number of tables: {len(db_info['tables'])}")
        print(f"   - Tables: {', '.join(db_info['tables'][:5])}{'...' if len(db_info['tables']) > 5 else ''}")

        # Train on schema (if tables exist)
        if db_info['tables']:
            print("\n🎯 Training Vanna on database schema...")
            training_summary = orchestrator.train_on_schema()
            print("✅ Training completed!")
            print(f"   - Training items: {training_summary.get('total_training_items', 'N/A')}")
            print(f"   - Tables analyzed: {training_summary.get('tables_analyzed', 'N/A')}")
            print(f"   - Relationships found: {training_summary.get('relationships_found', 'N/A')}")

            # Demo questions
            print("\n❓ Demo Questions:")
            demo_questions = [
                "How many tables are in this database?",
                "What are the column names in each table?",
                "Show me a sample of data from the first table"
            ]

            # Process demo questions
            results = orchestrator.ask_multiple_questions(demo_questions)

            print(f"\n📈 Query Results Summary:")
            print(f"   - Total questions: {results['total_questions']}")
            print(f"   - Successful queries: {results['successful_queries']}")
            print(f"   - Failed queries: {results['failed_queries']}")
            print(f"   - Average time per question: {results['average_time_per_question']:.2f}s")

            # Show individual results
            for i, result in enumerate(results['results'], 1):
                print(f"\n🔍 Question {i}: {result['question']}")
                if result['success']:
                    print(f"   ✅ SQL: {result['sql']}")
                    print(f"   📊 Rows: {result['row_count']}")
                    print(f"   ⚡ Time: {result['execution_time']:.2f}s")
                    # Show first few rows if available
                    if not result['result'].empty:
                        print("   📋 Sample data:")
                        print(result['result'].head().to_string(index=False))
                else:
                    print(f"   ❌ Error: {result['error']}")

        else:
            print("⚠️  No tables found in database. Creating some demo tables...")

            # Create demo tables for testing
            demo_sql_commands = [
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER REFERENCES customers(id),
                    total_amount DECIMAL(10,2) NOT NULL,
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                INSERT INTO customers (name, email) VALUES
                ('John Doe', 'john@example.com'),
                ('Jane Smith', 'jane@example.com'),
                ('Bob Johnson', 'bob@example.com')
                ON CONFLICT (email) DO NOTHING
                """,
                """
                INSERT INTO orders (customer_id, total_amount) VALUES
                (1, 99.99),
                (2, 149.50),
                (1, 75.25),
                (3, 200.00)
                """
            ]

            try:
                db_manager = orchestrator._get_database_manager()
                for sql in demo_sql_commands:
                    db_manager.run_sql(sql)
                print("✅ Demo tables created successfully!")

                # Retry training with new tables
                print("\n🎯 Training Vanna on new schema...")
                training_summary = orchestrator.train_on_schema()
                print("✅ Training completed!")

                # Test with demo questions
                demo_questions = [
                    "How many customers do we have?",
                    "What is the total revenue?",
                    "Which customer has the most orders?",
                    "Show me all customers and their total order amounts"
                ]

                results = orchestrator.ask_multiple_questions(demo_questions)

                print(f"\n📈 Demo Query Results:")
                for i, result in enumerate(results['results'], 1):
                    print(f"\n🔍 Question {i}: {result['question']}")
                    if result['success']:
                        print(f"   ✅ SQL: {result['sql']}")
                        print(f"   📊 Results:")
                        print(result['result'].to_string(index=False))
                    else:
                        print(f"   ❌ Error: {result['error']}")

            except Exception as e:
                print(f"❌ Error creating demo tables: {e}")

        # Performance metrics
        print("\n📈 Performance Metrics:")
        metrics = orchestrator.get_performance_metrics()

        if 'database_metrics' in metrics and metrics['database_metrics'].get('total_queries', 0) > 0:
            db_metrics = metrics['database_metrics']
            print(f"   Database:")
            print(f"     - Total queries: {db_metrics['total_queries']}")
            print(f"     - Average execution time: {db_metrics['avg_execution_time']:.3f}s")
            print(f"     - Total rows processed: {db_metrics['total_rows_processed']:,}")

        if 'query_interface_metrics' in metrics:
            qi_metrics = metrics['query_interface_metrics']
            if 'total_queries' in qi_metrics and qi_metrics['total_queries'] > 0:
                print(f"   Query Interface:")
                print(f"     - Cache hit rate: {qi_metrics['cache_hit_rate']:.1f}%")

        print("\n✅ Demo completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()