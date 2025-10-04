"""
Single script to run the entire document processing system.
Runs file watcher, document processors, and structured extractors concurrently.
"""

import multiprocessing
import logging
import signal
import sys
import os

# Pre-load onnxruntime DLLs before spawning child processes (Windows fix)
os.environ['OMP_NUM_THREADS'] = '1'
try:
    import onnxruntime
except ImportError:
    pass

def setup_logging():
    """Setup logging for the main process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_file_watcher():
    """Run the file watcher process."""
    try:
        from src.backend.doc_processing_system.utils.file_watcher import main
        main()
    except Exception as e:
        logging.error(f"File watcher failed: {e}")
        raise

def run_document_consumer():
    """Run the document processing consumer."""
    try:
        from src.backend.doc_processing_system.pipelines.document_processing.consumers.file_detected_consumer import FileDetectedConsumer
        consumer = FileDetectedConsumer(
            user_id="default",
            enable_vision_enhancement=False,
            enable_chunking=False,
            num_consumers=6
        )
        consumer.start()
    except Exception as e:
        logging.error(f"Document consumer failed: {e}")
        raise

def run_structured_consumer():
    """Run the structured extraction consumer."""
    try:
        from src.backend.doc_processing_system.pipelines.structured_extraction.consumers.document_pipeline_completed_consumer import main
        main()
    except Exception as e:
        logging.error(f"Structured consumer failed: {e}")
        raise

def run_api_server():
    """Run the FastAPI server."""
    try:
        import uvicorn
        uvicorn.run(
            "src.backend.api.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except Exception as e:
        logging.error(f"API server failed: {e}")
        raise

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logging.info("Received shutdown signal, terminating all processes...")
    sys.exit(0)

def main():
    """Main function to start all processes."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🚀 Starting Document Processing System...")
    logger.info("Components:")
    logger.info("  1. File Watcher - monitors for new files")
    logger.info("  2. Document Processors - 6 consumers processing documents")
    logger.info("  3. Structured Extractors - 6 consumers extracting structured data")
    logger.info("  4. FastAPI Server - REST API on port 8000")

    processes = []

    try:
        # Start file watcher
        logger.info("Starting File Watcher...")
        file_watcher_process = multiprocessing.Process(
            target=run_file_watcher,
            name="FileWatcher"
        )
        file_watcher_process.start()
        processes.append(file_watcher_process)

        # Start document processing consumer
        logger.info("Starting Document Processing Consumers...")
        doc_consumer_process = multiprocessing.Process(
            target=run_document_consumer,
            name="DocumentConsumer"
        )
        doc_consumer_process.start()
        processes.append(doc_consumer_process)

        # Start structured extraction consumer
        logger.info("Starting Structured Extraction Consumers...")
        struct_consumer_process = multiprocessing.Process(
            target=run_structured_consumer,
            name="StructuredConsumer"
        )
        struct_consumer_process.start()
        processes.append(struct_consumer_process)

        # Start FastAPI server
        logger.info("Starting FastAPI Server...")
        api_server_process = multiprocessing.Process(
            target=run_api_server,
            name="APIServer"
        )
        api_server_process.start()
        processes.append(api_server_process)

        logger.info("✅ All processes started successfully!")
        logger.info("📁 Drop files into: C:/Users/User/Projects/scaled_processing/data/documents/raw")
        logger.info("🌐 API available at: http://localhost:8000")
        logger.info("📖 API docs at: http://localhost:8000/docs")
        logger.info("🛑 Press Ctrl+C to stop all processes")

        # Wait for all processes
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
    finally:
        # Terminate all processes
        logger.info("Terminating all processes...")
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    logger.warning(f"Force killing process: {process.name}")
                    process.kill()

        logger.info("🛑 All processes stopped")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Required for Windows
    main()