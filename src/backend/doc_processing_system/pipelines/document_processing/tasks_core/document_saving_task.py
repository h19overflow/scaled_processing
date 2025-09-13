"""
Document saving task for document processing flow.
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger

from src.backend.doc_processing_system.pipelines.document_processing.utils.document_output_manager import DocumentOutputManager
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_schemas import create_message

@task(name="document-saving", retries=2)
def document_saving_task(
    vision_enhanced_markdown_path: str,
    document_id: str,
    content_length: int,
    page_count: int,
    raw_file_path: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """Save vision-enhanced document to structured directory using path-based I/O.

    Args:
        vision_enhanced_markdown_path: Path to vision-enhanced markdown file
        document_id: Document identifier
        content_length: Length of processed content
        page_count: Number of pages in document
        raw_file_path: Original file path for metadata
        user_id: User who uploaded the document
        
    Returns:
        Dict containing save results and file paths
    """
    logger = get_run_logger()
    logger.info(f"💾 Saving processed document: {document_id}")
    
    try:
        # Read vision-enhanced content from file
        enhanced_markdown_path = Path(vision_enhanced_markdown_path)
        if not enhanced_markdown_path.exists():
            raise FileNotFoundError(f"Vision-enhanced markdown not found: {vision_enhanced_markdown_path}")
        
        with open(enhanced_markdown_path, 'r', encoding='utf-8') as f:
            processed_content = f.read()
        
        logger.info(f"📖 Read {len(processed_content)} characters from vision-enhanced markdown")
        
        # Initialize output manager
        output_manager = DocumentOutputManager()
        
        # Prepare initial metadata for saving (without processed_content)
        file_path_obj = Path(raw_file_path)
        metadata = {
            "filename": file_path_obj.name,
            "page_count": page_count,
            "content_length": content_length,
            "file_type": file_path_obj.suffix.lower().replace('.', '') or 'pdf',
            "file_size": file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            "raw_file_path": raw_file_path,
            "vision_processing": True,
            "processing_timestamp": datetime.now().isoformat()
        }

        # Save processed document FIRST
        save_result = output_manager.save_processed_document(
            document_id, processed_content, metadata, user_id
        )
        
        # Read the ACTUAL saved content for Kafka message
        final_processed_content = ""
        if save_result.get("status") == "saved" and save_result.get("processed_file_path"):
            try:
                with open(save_result["processed_file_path"], 'r', encoding='utf-8') as f:
                    final_processed_content = f.read()
                logger.info(f"📖 Read {len(final_processed_content)} characters from saved file: {save_result['processed_file_path']}")
            except Exception as e:
                logger.error(f"Failed to read saved file: {e}")
                final_processed_content = processed_content  # Fallback to original
        
        # Now prepare Kafka metadata with the ACTUAL saved content
        kafka_metadata = metadata.copy()
        kafka_metadata["processed_content"] = final_processed_content
        
        # Create a kafka message and send it using the ProducerHandler
        try:
            message = create_message(event_type="document_pipeline_completed", data=kafka_metadata, source="document_processing")
            kafka_producer = ProducerHandler("localhost:9092")

            result = kafka_producer.produce_message(topic="document_pipeline_completed",key= file_path_obj.name,value=message)
            if result:
                logger.info(f"✅ Message sent for document: {file_path_obj.name}")
            else:
                logger.error(f"❌ Failed to send message for document: {file_path_obj.name}")

        except Exception as e:
            logger.error(f"Failed to send message for document: {file_path_obj.name} ERROR: {e}")
        
        if save_result["status"] == "saved":
            logger.info(f"✅ Document saved successfully: {save_result['processed_file_path']}")
        else:
            logger.error(f"❌ Failed to save document: {save_result.get('error')}")
            
        return {
            "document_id": document_id,
            "save_result": save_result,
            "status": "completed" if save_result["status"] == "saved" else "error",
            "processed_file_path": save_result.get("processed_file_path"),
            "document_directory": save_result.get("document_directory"),
            "content_length": content_length,
            "page_count": page_count,
            "kafka_message": message if 'message' in locals() else None,
            "final_content_length": len(final_processed_content)
        }
        
    except Exception as e:
        logger.error(f"❌ Document saving failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Document saving failed: {e}"
        }


def main():
    """Test the document saving task with a real processed file."""
    import json
    
    # Use an existing processed file for testing
    test_vision_path = "data/documents/processed/batch1-0001/batch1-0001_processed.md"
    test_raw_path = "data/documents/raw/batch1-0001.jpg"
    
    print("🧪 Testing Document Saving Task")
    print(f"📄 Vision file: {test_vision_path}")
    print(f"📁 Raw file: {test_raw_path}")
    
    try:
        # Run the document saving task
        result = document_saving_task(
            vision_enhanced_markdown_path=test_vision_path,
            document_id="test-batch1-0001",
            content_length=1972,
            page_count=1,
            raw_file_path=test_raw_path,
            user_id="test_user"
        )
        
        print("\n✅ Task Result:")
        print(f"Status: {result.get('status')}")
        print(f"Final content length: {result.get('final_content_length', 'N/A')}")
        
        # Print the Kafka message if available
        if result.get('kafka_message'):
            print("\n📨 Kafka Message:")
            message_obj = json.loads(result['kafka_message'])
            print(f"Event Type: {message_obj.get('event_type')}")
            print(f"Source: {message_obj.get('source')}")
            print(f"Data keys: {list(message_obj.get('data', {}).keys())}")
            print(f"Processed content length: {len(message_obj.get('data', {}).get('processed_content', ''))}")
            
            # Show first 200 chars of processed content
            processed_content = message_obj.get('data', {}).get('processed_content', '')
            if processed_content:
                print(f"\n📝 Content preview (first 200 chars):")
                print(processed_content[:200] + "..." if len(processed_content) > 200 else processed_content)
            else:
                print("\n❌ NO PROCESSED CONTENT IN MESSAGE!")
        else:
            print("\n❌ No Kafka message generated")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    main()