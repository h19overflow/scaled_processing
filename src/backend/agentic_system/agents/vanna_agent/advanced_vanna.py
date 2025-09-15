"""
Advanced Vanna implementation combining ChromaDB and Google Gemini
"""

import os
import time
import logging
from typing import Dict
from dotenv import load_dotenv

from vanna.faiss import FAISS
from vanna.google import GoogleGeminiChat

load_dotenv()


class AdvancedVanna(FAISS, GoogleGeminiChat):
    """Enhanced Vanna implementation with FAISS vector store and Gemini integration"""

    def __init__(self, config: Dict = None):
        """Initialize AdvancedVanna with optimized configurations"""
        # FAISS configuration - use absolute path
        self.config = config
        import os
        faiss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vanna_faiss_db')
        os.makedirs(faiss_path, exist_ok=True)

        faiss_config = {
            'path': faiss_path,
            'dimension': 768  # Standard embedding dimension
        }

        # Advanced Gemini Configuration
        gemini_config = {
            'api_key': os.getenv('GEMINI_API_KEY'),
            'model': 'gemini-2.0-flash',
            'temperature': 0.1,
            'max_tokens': 8192,
            'safety_settings': {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_MEDIUM_AND_ABOVE'
            }
        }

        FAISS.__init__(self, config=faiss_config)
        GoogleGeminiChat.__init__(self, config=gemini_config)

        # Performance tracking
        self.query_cache = {}
        self.performance_metrics = []

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_training_plan_generic(self, df):
        """Get generic training plan from dataframe"""
        return super().get_training_plan_generic(df)

    def train(self, **kwargs):
        """Train the model with provided data"""
        return super().train(**kwargs)

    def generate_sql(self, question: str) -> str:
        """Generate SQL query from natural language question"""
        return super().generate_sql(question)

    def get_training_data(self):
        """Get current training data"""
        return super().get_training_data()

    def run_sql(self, sql: str):
        """Run SQL query - will be overridden by database manager"""
        raise NotImplementedError("SQL execution should be handled by DatabaseManager")

if __name__ == "__main__":
    vanna = AdvancedVanna()
    vanna.get_training_data()