"""
Optimized query interface with caching and performance metrics
"""

import time
import pandas as pd
from typing import Dict
import logging
from dotenv import load_dotenv

load_dotenv()


class OptimizedQueryInterface:
    """Enhanced query interface with caching and performance metrics"""

    def __init__(self, vanna_instance):
        """Initialize optimized query interface"""
        self.vn = vanna_instance

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def smart_ask(self, question: str, use_cache: bool = True) -> Dict:
        """Enhanced ask with caching and performance metrics"""
        question_hash = hash(question)

        # Check cache first
        if use_cache and question_hash in self.vn.query_cache:
            self.logger.info("Retrieved from cache")
            return self.vn.query_cache[question_hash]

        start_time = time.time()

        try:
            # Generate SQL with explanation
            sql = self.vn.generate_sql(question)
            self.logger.info(f"Generated SQL: {sql}")

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

            self.logger.info(f"Query successful: {len(result_df)} rows in {execution_time:.2f}s")
            return response

        except Exception as e:
            execution_time = time.time() - start_time
            error_response = {
                'question': question,
                'error': str(e),
                'execution_time': execution_time,
                'success': False
            }
            self.logger.error(f"Query failed after {execution_time:.2f}s: {str(e)}")
            return error_response

    def ask_multiple(self, questions: list, use_cache: bool = True) -> Dict:
        """Process multiple questions and return results"""
        results = []
        total_start_time = time.time()

        for i, question in enumerate(questions, 1):
            self.logger.info(f"Processing question {i}/{len(questions)}: {question}")
            result = self.smart_ask(question, use_cache)
            results.append(result)

        total_time = time.time() - total_start_time

        return {
            'results': results,
            'total_questions': len(questions),
            'successful_queries': sum(1 for r in results if r['success']),
            'failed_queries': sum(1 for r in results if not r['success']),
            'total_execution_time': total_time,
            'average_time_per_question': total_time / len(questions) if questions else 0
        }

    def get_performance_summary(self) -> Dict:
        """Get performance analytics"""
        if not self.vn.performance_metrics:
            return {"message": "No performance metrics available"}

        df_metrics = pd.DataFrame(self.vn.performance_metrics)
        cache_hit_rate = len(self.vn.query_cache) / len(df_metrics) * 100 if df_metrics is not None and len(df_metrics) > 0 else 0

        return {
            'total_queries': len(df_metrics),
            'average_execution_time': df_metrics['execution_time'].mean(),
            'total_rows_processed': df_metrics['rows_returned'].sum(),
            'cache_hit_rate': cache_hit_rate,
            'fastest_query': df_metrics['execution_time'].min(),
            'slowest_query': df_metrics['execution_time'].max()
        }

    def clear_cache(self):
        """Clear the query cache"""
        cache_size = len(self.vn.query_cache)
        self.vn.query_cache.clear()
        self.logger.info(f"Cleared {cache_size} cached queries")

    def get_cache_info(self) -> Dict:
        """Get information about cached queries"""
        return {
            'cached_queries': len(self.vn.query_cache),
            'cache_keys': list(self.vn.query_cache.keys())
        }