"""
Main orchestrator for the Vanna agent system
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

from src.backend.agentic_system.agents.vanna_agent.advanced_vanna import AdvancedVanna
from src.backend.agentic_system.agents.vanna_agent.database_manager import DatabaseManager
from src.backend.agentic_system.agents.vanna_agent.schema_analyzer import SchemaAnalyzer
from src.backend.agentic_system.agents.vanna_agent.query_interface import OptimizedQueryInterface

load_dotenv()


class VannaOrchestrator:
    """Main orchestrator that coordinates all Vanna components"""

    def __init__(self, connection_string: str):
        """Initialize the Vanna orchestrator with database connection"""
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize components
        self.logger.info("Initializing Vanna components...")

        # Create Vanna instance
        self._vn = AdvancedVanna()

        # Create database manager
        self._db_manager = DatabaseManager(connection_string)

        # Wire SQL execution to database manager
        self._vn.run_sql = self._db_manager.run_sql
        self._vn.run_sql_is_set = True

        # Create schema analyzer
        self._schema_analyzer = SchemaAnalyzer(self._db_manager, self._vn)

        # Create query interface
        self._query_interface = OptimizedQueryInterface(self._vn)

        self.logger.info("Vanna orchestrator initialized successfully")

    def test_connection(self) -> bool:
        """Test database connection"""
        return self._db_manager.test_connection()

    def train_on_schema(self) -> Dict:
        """Train Vanna on the database schema"""
        return self._schema_analyzer.run_advanced_training()

    def ask_question(self, question: str, use_cache: bool = True) -> Dict:
        """Ask a natural language question and get SQL results"""
        return self._query_interface.smart_ask(question, use_cache)

    def ask_multiple_questions(self, questions: list, use_cache: bool = True) -> Dict:
        """Process multiple questions"""
        return self._query_interface.ask_multiple(questions, use_cache)

    def get_database_info(self) -> Dict:
        """Get database connection details and statistics"""
        return self._db_manager.get_connection_details()

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics from both database and query interface"""
        db_metrics = self._db_manager.get_performance_summary()
        query_metrics = self._query_interface.get_performance_summary()

        return {
            'database_metrics': db_metrics,
            'query_interface_metrics': query_metrics
        }

    def clear_cache(self):
        """Clear query cache"""
        self._query_interface.clear_cache()

    def get_training_data_summary(self) -> Dict:
        """Get summary of training data"""
        try:
            training_data = self._vn.get_training_data()
            return {
                'total_training_items': len(training_data),
                'training_data_available': True
            }
        except Exception as e:
            return {
                'error': str(e),
                'training_data_available': False
            }

    def save_session_results(self, results: Dict, filename: str = None) -> str:
        """Save session results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vanna_session_{timestamp}.json"

        try:
            # Create results directory if it doesn't exist
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            os.makedirs(results_dir, exist_ok=True)

            filepath = os.path.join(results_dir, filename)

            # Prepare results with metadata
            output_results = {
                "timestamp": datetime.now().isoformat(),
                "session_metadata": {
                    "orchestrator": "VannaOrchestrator",
                    "vector_store": "FAISS",
                    "llm_model": "Gemini",
                    "database_type": self._db_manager.get_connection_details().get('type', 'unknown')
                },
                "results": results
            }

            # Save to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_results, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Session results saved to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save session results: {e}")
            return None

    def export_training_data(self, filename: str = None) -> str:
        """Export training data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_data_{timestamp}.json"

        try:
            training_data = self._vn.get_training_data()

            # Create results directory if it doesn't exist
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            os.makedirs(results_dir, exist_ok=True)

            filepath = os.path.join(results_dir, filename)

            training_export = {
                "timestamp": datetime.now().isoformat(),
                "training_data_count": len(training_data),
                "database_info": self.get_database_info(),
                "training_data": training_data
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(training_export, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Training data exported to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to export training data: {e}")
            return None

    # HELPER FUNCTIONS

    def _get_vanna_instance(self):
        """Get the underlying Vanna instance"""
        return self._vn

    def _get_database_manager(self):
        """Get the database manager instance"""
        return self._db_manager

    def _get_schema_analyzer(self):
        """Get the schema analyzer instance"""
        return self._schema_analyzer

    def _get_query_interface(self):
        """Get the query interface instance"""
        return self._query_interface