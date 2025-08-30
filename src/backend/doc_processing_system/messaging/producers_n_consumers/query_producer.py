"""
Query-specific Kafka producer for query processing events.
Handles RAG, structured, and hybrid query events using existing data models.
"""

from .base_producer import BaseKafkaProducer, create_message_key
from ...data_models.query import UserQuery, RAGQueryResult, StructuredQueryResult, HybridQueryResult
from ...data_models.events import (
    QueryReceivedEvent,
    RAGQueryCompleteEvent, 
    StructuredQueryCompleteEvent,
    HybridQueryCompleteEvent
)


class QueryProducer(BaseKafkaProducer):
    """
    Producer for query processing events.
    Publishes events for query reception and completion of different query types.
    """
    
    def get_default_topic(self) -> str:
        """Default topic for query events."""
        return "query-received"
    
    def send_query_received(self, user_query: UserQuery) -> bool:
        """
        Send query received event.
        
        Args:
            user_query: User query data
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = QueryReceivedEvent(
                query_id=user_query.query_id,
                user_query=user_query
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key using query_id and user_id
            message_key = create_message_key(
                document_id=user_query.query_id,
                user_id=user_query.user_id
            )
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Query received event sent: {user_query.query_id} "
                    f"(type: {user_query.query_type})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send query received event: {e}")
            return False
    
    def send_rag_query_complete(self, query_id: str, rag_result: RAGQueryResult) -> bool:
        """
        Send RAG query complete event.
        
        Args:
            query_id: Query identifier
            rag_result: RAG query result
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = RAGQueryCompleteEvent(
                query_id=query_id,
                rag_result=rag_result
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(query_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"RAG query complete event sent: {query_id} "
                    f"(confidence: {rag_result.confidence_score})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send RAG query complete event: {e}")
            return False
    
    def send_structured_query_complete(self, query_id: str, structured_result: StructuredQueryResult) -> bool:
        """
        Send structured query complete event.
        
        Args:
            query_id: Query identifier
            structured_result: Structured query result
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = StructuredQueryCompleteEvent(
                query_id=query_id,
                structured_result=structured_result
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(query_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Structured query complete event sent: {query_id} "
                    f"({len(structured_result.filtered_data)} results)"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send structured query complete event: {e}")
            return False
    
    def send_hybrid_query_complete(self, query_id: str, hybrid_result: HybridQueryResult) -> bool:
        """
        Send hybrid query complete event.
        
        Args:
            query_id: Query identifier
            hybrid_result: Hybrid query result
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = HybridQueryCompleteEvent(
                query_id=query_id,
                hybrid_result=hybrid_result
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(query_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Hybrid query complete event sent: {query_id} "
                    f"(confidence: {hybrid_result.confidence_score})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send hybrid query complete event: {e}")
            return False