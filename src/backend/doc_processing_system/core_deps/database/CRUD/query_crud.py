"""
Query CRUD operations.
Handles all database operations related to query logs and results.
"""

from typing import List
from sqlalchemy import desc

from .base_repository import BaseRepository
from ..models import QueryLogModel, QueryResultModel
from ....data_models.query import QueryLog, QueryResult


class QueryCRUD(BaseRepository):
    """CRUD operations for query log and result entities."""
    
    def create_query_log(self, query_log: QueryLog) -> str:
        """Create query log and return its ID.
        
        Args:
            query_log: QueryLog object to create
            
        Returns:
            str: Created query log ID
            
        Raises:
            Exception: If query log creation fails
        """
        try:
            with self.connection_manager.get_session() as session:
                log_model = QueryLogModel(
                    query_id=query_log.query_id,
                    user_id=query_log.user_id,
                    query_text=query_log.query_text,
                    query_type=query_log.query_type,
                    filters=query_log.filters,
                    response_time_ms=query_log.response_time_ms
                )
                
                session.add(log_model)
                session.flush()
                log_id = str(log_model.id)
                
                self._log_operation("Created query log", log_id, 
                                  f"user: {query_log.user_id}, type: {query_log.query_type}")
                return log_id
        
        except Exception as e:
            self.logger.error(f"Failed to create query log: {e}")
            raise
    
    def create_query_result(self, query_result: QueryResult) -> str:
        """Create query result and return its ID.
        
        Args:
            query_result: QueryResult object to create
            
        Returns:
            str: Created query result ID
            
        Raises:
            Exception: If query result creation fails
        """
        try:
            with self.connection_manager.get_session() as session:
                result_model = QueryResultModel(
                    query_id=query_result.query_id,
                    result_type=query_result.result_type,
                    result_data=query_result.result_data,
                    confidence_score=query_result.confidence_score,
                    source_documents=query_result.source_documents
                )
                
                session.add(result_model)
                session.flush()
                result_id = str(result_model.id)
                
                self._log_operation("Created query result", result_id,
                                  f"query: {query_result.query_id}, type: {query_result.result_type}")
                return result_id
        
        except Exception as e:
            self.logger.error(f"Failed to create query result: {e}")
            raise
    
    def get_query_logs_by_user(self, user_id: str, limit: int = 50) -> List[QueryLog]:
        """Get query logs by user ID.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of query logs to return
            
        Returns:
            List[QueryLog]: List of user's query logs
        """
        try:
            with self.connection_manager.get_session() as session:
                log_models = session.query(QueryLogModel).filter(
                    QueryLogModel.user_id == user_id
                ).order_by(desc(QueryLogModel.created_at)).limit(limit).all()
                
                query_logs = [self._model_to_query_log(log) for log in log_models]
                
                self._log_operation("Retrieved query logs by user", user_id,
                                  f"count: {len(query_logs)}")
                return query_logs
        
        except Exception as e:
            self.logger.error(f"Failed to get query logs for user {user_id}: {e}")
            raise
    
    def get_query_results(self, query_id: str) -> List[QueryResult]:
        """Get all results for a query.
        
        Args:
            query_id: Query ID to get results for
            
        Returns:
            List[QueryResult]: List of query results
        """
        try:
            with self.connection_manager.get_session() as session:
                result_models = session.query(QueryResultModel).filter(
                    QueryResultModel.query_id == query_id
                ).order_by(QueryResultModel.created_at).all()
                
                query_results = [self._model_to_query_result(result) for result in result_models]
                
                self._log_operation("Retrieved query results", query_id,
                                  f"count: {len(query_results)}")
                return query_results
        
        except Exception as e:
            self.logger.error(f"Failed to get query results for query {query_id}: {e}")
            raise
    
    def get_query_log_by_id(self, query_id: str) -> QueryLog:
        """Get query log by query ID.
        
        Args:
            query_id: Query ID to retrieve
            
        Returns:
            QueryLog: Query log object
            
        Raises:
            ValueError: If query log not found
        """
        try:
            with self.connection_manager.get_session() as session:
                log_model = session.query(QueryLogModel).filter(
                    QueryLogModel.query_id == query_id
                ).first()
                
                if not log_model:
                    raise ValueError(f"Query log not found: {query_id}")
                
                return self._model_to_query_log(log_model)
        
        except Exception as e:
            self.logger.error(f"Failed to get query log {query_id}: {e}")
            raise
    
    def get_recent_queries(self, limit: int = 100) -> List[QueryLog]:
        """Get recent query logs across all users.
        
        Args:
            limit: Maximum number of query logs to return
            
        Returns:
            List[QueryLog]: List of recent query logs
        """
        try:
            with self.connection_manager.get_session() as session:
                log_models = session.query(QueryLogModel).order_by(
                    desc(QueryLogModel.created_at)
                ).limit(limit).all()
                
                query_logs = [self._model_to_query_log(log) for log in log_models]
                
                self._log_operation("Retrieved recent queries", details=f"count: {len(query_logs)}")
                return query_logs
        
        except Exception as e:
            self.logger.error(f"Failed to get recent queries: {e}")
            raise
    
    def delete_old_queries(self, days_old: int = 30) -> int:
        """Delete query logs older than specified days.
        
        Args:
            days_old: Number of days to keep queries
            
        Returns:
            int: Number of query logs deleted
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with self.connection_manager.get_session() as session:
                deleted_count = session.query(QueryLogModel).filter(
                    QueryLogModel.created_at < cutoff_date
                ).delete()
                
                self._log_operation("Deleted old query logs", details=f"count: {deleted_count}, older than {days_old} days")
                return deleted_count
        
        except Exception as e:
            self.logger.error(f"Failed to delete old queries: {e}")
            raise
    
    def _model_to_query_log(self, log_model: QueryLogModel) -> QueryLog:
        """Convert QueryLogModel to QueryLog.
        
        Args:
            log_model: QueryLogModel instance
            
        Returns:
            QueryLog: Converted QueryLog object
        """
        return QueryLog(
            query_id=log_model.query_id,
            user_id=log_model.user_id,
            query_text=log_model.query_text,
            query_type=log_model.query_type,
            filters=log_model.filters or {},
            response_time_ms=log_model.response_time_ms,
            created_at=log_model.created_at
        )
    
    def _model_to_query_result(self, result_model: QueryResultModel) -> QueryResult:
        """Convert QueryResultModel to QueryResult.
        
        Args:
            result_model: QueryResultModel instance
            
        Returns:
            QueryResult: Converted QueryResult object
        """
        return QueryResult(
            query_id=result_model.query_id,
            result_type=result_model.result_type,
            result_data=result_model.result_data or {},
            confidence_score=result_model.confidence_score,
            source_documents=result_model.source_documents or [],
            created_at=result_model.created_at
        )
