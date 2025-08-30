"""
Extraction-specific Kafka producer for structured extraction events.
Handles field discovery, agent scaling, and extraction events using existing data models.
"""

from typing import List

from .base_producer import BaseKafkaProducer, create_message_key
from ..data_models.extraction import FieldSpecification, AgentScalingConfig, ExtractionResult
from ..data_models.events import (
    FieldInitCompleteEvent, 
    AgentScalingCompleteEvent, 
    ExtractionTaskMessage,
    ExtractionCompleteEvent
)


class ExtractionProducer(BaseKafkaProducer):
    """
    Producer for structured extraction workflow events.
    Publishes events for field discovery, agent scaling, and extraction completion.
    """
    
    def get_default_topic(self) -> str:
        """Default topic for extraction events."""
        return "field-init-complete"
    
    def send_field_init_complete(
        self, 
        document_id: str, 
        field_specifications: List[FieldSpecification],
        discovery_method: str = "automatic"
    ) -> bool:
        """
        Send field initialization complete event.
        
        Args:
            document_id: Document identifier
            field_specifications: List of discovered field specifications
            discovery_method: Method used for field discovery
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = FieldInitCompleteEvent(
                document_id=document_id,
                field_specifications=field_specifications,
                discovery_method=discovery_method
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Field init complete event sent: {document_id} "
                    f"({len(field_specifications)} fields discovered via {discovery_method})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send field init complete event: {e}")
            return False
    
    def send_agent_scaling_complete(self, document_id: str, scaling_config: AgentScalingConfig) -> bool:
        """
        Send agent scaling complete event.
        
        Args:
            document_id: Document identifier
            scaling_config: Agent scaling configuration
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = AgentScalingCompleteEvent(
                document_id=document_id,
                scaling_config=scaling_config
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Agent scaling complete event sent: {document_id} "
                    f"({scaling_config.agent_count} agents for {scaling_config.page_count} pages)"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send agent scaling complete event: {e}")
            return False
    
    def send_extraction_task(self, extraction_task: ExtractionTaskMessage) -> bool:
        """
        Send extraction task to agent workers.
        
        Args:
            extraction_task: Extraction task message
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Convert to dict for Kafka
            event_data = extraction_task.dict()
            
            # Create message key using task_id for even distribution
            message_key = f"task_{extraction_task.task_id}"
            
            # Publish to extraction tasks topic
            success = self.publish_event(
                topic=extraction_task.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Extraction task sent: {extraction_task.task_id} "
                    f"(agent: {extraction_task.agent_id}, pages: {extraction_task.page_range})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send extraction task: {e}")
            return False
    
    def send_extraction_complete(
        self, 
        document_id: str, 
        extraction_results: List[ExtractionResult],
        completion_status: str = "completed"
    ) -> bool:
        """
        Send extraction complete event.
        
        Args:
            document_id: Document identifier
            extraction_results: List of extraction results from all agents
            completion_status: Overall completion status
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Create event using existing data model
            event = ExtractionCompleteEvent(
                document_id=document_id,
                extraction_results=extraction_results,
                completion_status=completion_status
            )
            
            # Convert to dict for Kafka
            event_data = event.dict()
            
            # Create message key
            message_key = create_message_key(document_id)
            
            # Publish event
            success = self.publish_event(
                topic=event.topic,
                event_data=event_data,
                key=message_key
            )
            
            if success:
                self.logger.info(
                    f"Extraction complete event sent: {document_id} "
                    f"({len(extraction_results)} results, status: {completion_status})"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send extraction complete event: {e}")
            return False