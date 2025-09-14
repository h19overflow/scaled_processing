"""
Demo script for the modular Vanna agent system
"""
# TODO , Explore Vanna More current error: Traceback (most recent call last):
#   File "C:\Users\User\Projects\scaled_processing\src\backend\agentic_system\agents\vanna_agent\demo.py", line 80, in main
#     results = orchestrator.vn.generate_sql(demo_questions)
#               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\User\Projects\scaled_processing\src\backend\agentic_system\agents\vanna_agent\advanced_vanna.py", line 67, in generate_sql
#     return super().generate_sql(question)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\vanna\base\base.py", line 124, in generate_sql
#     question_sql_list = self.get_similar_question_sql(question, **kwargs)
#                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\vanna\faiss\faiss.py", line 124, in get_similar_question_sql
#     return self._get_similar(self.sql_index, self.sql_metadata, question, self.n_results_sql)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\vanna\faiss\faiss.py", line 119, in _get_similar
#     embedding = self.generate_embedding(text)
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\vanna\faiss\faiss.py", line 89, in generate_embedding
#     assert embedding.shape[0] == self.embedding_dim, \
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# AssertionError: Embedding dimension mismatch: expected 384, got 1
import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from vanna_orchestrator import VannaOrchestrator
except ImportError:
    from src.backend.agentic_system.agents.vanna_agent.vanna_orchestrator import VannaOrchestrator

load_dotenv()




def main():
    """Main demo function"""
    print("🚀 Vanna Agent Modular Demo")
    print("=" * 50)

    # Initialize results dictionary
    demo_results = {
        "demo_info": {
            "name": "Vanna Agent Modular Demo",
            "version": "1.0.0",
            "description": "Demo of modular Vanna agent with FAISS vector store and PostgreSQL"
        },
        "status": "started"
    }

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
        demo_results["database_info"] = db_info
        print(f"   - Database type: {db_info['type']}")
        print(f"   - Number of tables: {len(db_info['tables'])}")
        print(f"   - Tables: {', '.join(db_info['tables'][:5])}{'...' if len(db_info['tables']) > 5 else ''}")

        # Train on schema (if tables exist)
        if db_info['tables']:
            print("\n🎯 Training Vanna on database schema...")
            # training_summary = orchestrator.train_on_schema()
            # demo_results["training_summary"] = training_summary
            # print("✅ Training completed!")
            # print(f"   - Training items: {training_summary.get('total_training_items', 'N/A')}")
            # print(f"   - Tables analyzed: {training_summary.get('tables_analyzed', 'N/A')}")
            # print(f"   - Relationships found: {training_summary.get('relationships_found', 'N/A')}")

            # Demo questions
            print("\n❓ Demo Questions:")
            demo_questions = [
                "What is the count of line itmes in the table structured_documents?"
            ]

            # Process demo questions
            results = orchestrator.vn.ask(demo_questions)
            demo_results["query_results"] = results

            # print(f"\n📈 Query Results Summary:")
            # print(f"   - Total questions: {results['total_questions']}")
            # print(f"   - Successful queries: {results['successful_queries']}")
            # print(f"   - Failed queries: {results['failed_queries']}")
            # print(f"   - Average time per question: {results['average_time_per_question']:.2f}s")

            # Show individual results
            # for i, result in enumerate(results['results'], 1):
            #     print(f"\n🔍 Question {i}: {result['question']}")
            #     if result['success']:
            #         print(f"   ✅ SQL: {result['sql']}")
            #         print(f"   📊 Rows: {result['row_count']}")
            #         print(f"   ⚡ Time: {result['execution_time']:.2f}s")
            #         # Show first few rows if available
            #         if not result['result'].empty:
            #             print("   📋 Sample data:")
            #             print(result['result'].head().to_string(index=False))
            #     else:
            #         print(f"   ❌ Error: {result['error']}")
            print(results)

        else:
            print("⚠️  No tables found in database. Creating some demo tables...")
        # Performance metrics
        print("\n📈 Performance Metrics:")
        metrics = orchestrator.get_performance_metrics()
        demo_results["performance_metrics"] = metrics

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

        demo_results["status"] = "completed"
        print("\n✅ Demo completed successfully!")

        # Save results to JSON

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        demo_results["status"] = "failed"
        demo_results["error"] = str(e)

        # Save error results to JSON

        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()