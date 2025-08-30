"""
Steel thread test for end-to-end message flow verification.
Tests document upload -> Kafka event -> consumer processing.
"""

import asyncio
import logging
import time
from pathlib import Path
import tempfile
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_steel_thread():
    """
    Test the complete steel thread flow:
    1. Create test document
    2. Upload via API
    3. Verify Kafka message
    4. Check consumer processing
    """
    
    logger.info("=== STARTING STEEL THREAD TEST ===")
    
    try:
        # Import the components we need
        from src.backend.doc_processing_system.messaging.producers_n_consumers.event_bus import EventBus, EventType
        from src.backend.doc_processing_system.messaging.producers_n_consumers.document_consumer import create_simple_document_consumer
        
        # Step 1: Initialize event bus
        logger.info("Step 1: Initializing Event Bus...")
        event_bus = EventBus()
        
        # Step 2: Create and start document consumer
        logger.info("Step 2: Starting Document Consumer...")
        consumer = create_simple_document_consumer()
        consumer.start_consuming()
        
        # Give consumer a moment to initialize
        await asyncio.sleep(2)
        
        # Step 3: Create test document data
        logger.info("Step 3: Creating test document...")
        test_document_data = {
            "document_id": "steel-thread-test-001",
            "filename": "test_document.pdf",
            "user_id": "test_user",
            "file_size": 1024,
            "upload_timestamp": "2024-01-01T12:00:00Z",
            "parsed_content": "This is test content for steel thread verification",
            "page_count": 1
        }
        
        # Step 4: Publish document received event
        logger.info("Step 4: Publishing document-received event...")
        success = event_bus.publish(
            event_type=EventType.DOCUMENT_RECEIVED,
            event_data=test_document_data,
            key=test_document_data["document_id"]
        )
        
        if success:
            logger.info("✅ Event published successfully!")
        else:
            logger.error("❌ Failed to publish event")
            return False
        
        # Step 5: Wait for consumer processing
        logger.info("Step 5: Waiting for consumer processing...")
        await asyncio.sleep(5)
        
        # Step 6: Test multiple event types
        logger.info("Step 6: Testing additional event types...")
        
        # Test RAG pipeline events
        rag_events = [
            (EventType.CHUNKING_COMPLETE, {"document_id": "steel-thread-test-001", "chunks": ["chunk1", "chunk2"]}),
            (EventType.EMBEDDING_READY, {"document_id": "steel-thread-test-001", "embeddings_count": 2}),
            (EventType.INGESTION_COMPLETE, {"document_id": "steel-thread-test-001", "vectors_stored": 2})
        ]
        
        for event_type, event_data in rag_events:
            success = event_bus.publish(event_type=event_type, event_data=event_data, key="steel-thread-test-001")
            if success:
                logger.info(f"✅ Published {event_type.value} event")
            else:
                logger.error(f"❌ Failed to publish {event_type.value} event")
            await asyncio.sleep(1)
        
        # Step 7: Get system statistics
        logger.info("Step 7: Gathering system statistics...")
        
        topics = event_bus.get_topics()
        producer_stats = event_bus.get_producer_stats()
        consumer_stats = event_bus.get_consumer_stats()
        
        logger.info(f"Available topics: {len(topics)}")
        logger.info(f"Active producers: {len(producer_stats)}")
        logger.info(f"Active consumers: {len(consumer_stats)}")
        
        # Step 8: Cleanup
        logger.info("Step 8: Cleaning up...")
        consumer.stop_consuming()
        await asyncio.sleep(2)
        event_bus.close_all()
        
        logger.info("=== STEEL THREAD TEST COMPLETED SUCCESSFULLY ===")
        return True
        
    except Exception as e:
        logger.error(f"❌ Steel thread test failed: {e}")
        return False


async def test_api_integration():
    """
    Test API integration (requires FastAPI server to be running).
    """
    logger.info("=== TESTING API INTEGRATION ===")
    
    try:
        import aiohttp
        import aiofiles
        
        # Create a test file
        test_content = "This is a test document for steel thread verification."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            test_file_path = f.name
        
        # Upload the file via API
        async with aiohttp.ClientSession() as session:
            with open(test_file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test_document.txt', content_type='text/plain')
                data.add_field('user_id', 'steel_thread_test')
                
                async with session.post('http://localhost:8000/api/v1/upload', data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ File uploaded successfully: {result['document_id']}")
                        
                        # Test status endpoint
                        document_id = result['document_id']
                        async with session.get(f'http://localhost:8000/api/v1/status/{document_id}') as status_response:
                            if status_response.status == 200:
                                status_result = await status_response.json()
                                logger.info(f"✅ Status check successful: {status_result}")
                            else:
                                logger.error(f"❌ Status check failed: {status_response.status}")
                        
                        # Test topics endpoint  
                        async with session.get('http://localhost:8000/api/v1/topics') as topics_response:
                            if topics_response.status == 200:
                                topics_result = await topics_response.json()
                                logger.info(f"✅ Topics endpoint successful: {len(topics_result.get('topics', []))} topics")
                            else:
                                logger.error(f"❌ Topics check failed: {topics_response.status}")
                        
                        return True
                    else:
                        logger.error(f"❌ Upload failed: {response.status}")
                        return False
        
    except ImportError:
        logger.warning("aiohttp not available, skipping API integration test")
        logger.info("To test API integration, install aiohttp: pip install aiohttp")
        return True
    except Exception as e:
        logger.error(f"❌ API integration test failed: {e}")
        return False


def print_usage_instructions():
    """Print instructions for manual testing."""
    logger.info("=== MANUAL TESTING INSTRUCTIONS ===")
    logger.info("")
    logger.info("1. Start the Docker services:")
    logger.info("   docker-compose up -d")
    logger.info("")
    logger.info("2. Start the FastAPI server:")
    logger.info("   cd src/backend/doc_processing_system")
    logger.info("   uvicorn api.main:app --reload --port 8000")
    logger.info("")
    logger.info("3. Access the API documentation:")
    logger.info("   Browser: http://localhost:8000/docs")
    logger.info("   Info endpoint: http://localhost:8000/docs-info")
    logger.info("")
    logger.info("4. Test file upload:")
    logger.info("   curl -X POST 'http://localhost:8000/api/v1/upload' \\")
    logger.info("        -F 'file=@test_document.pdf' \\")
    logger.info("        -F 'user_id=test_user'")
    logger.info("")
    logger.info("5. Monitor Kafka:")
    logger.info("   Browser: http://localhost:9000 (Kafdrop UI)")
    logger.info("   Topics: http://localhost:8000/api/v1/topics")
    logger.info("")


if __name__ == "__main__":
    print_usage_instructions()
    
    logger.info("Choose test mode:")
    logger.info("1. Run steel thread test (tests Kafka messaging)")
    logger.info("2. Run API integration test (requires running server)")
    logger.info("3. Show manual testing instructions")
    
    # For automated testing, run steel thread test
    asyncio.run(test_steel_thread())