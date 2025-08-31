"""
Document Processing Orchestrator - Unified service runner.
Coordinates FileWatcherService and PrefectFlowConsumer for automated document processing.
"""
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from .file_watcher import FileWatcherService
from .prefect_flow_consumer import PrefectFlowConsumer
from ...config.settings import get_settings

class DocumentProcessingOrchestrator:
    """
    Orchestrates the complete automated document processing pipeline.
    
    Components:
    1. FileWatcherService - Monitors data/documents/raw/ for new files
    2. PrefectFlowConsumer(s) - Consumes file-detected events and triggers Prefect flows
    
    Supports scaling with multiple Prefect consumers for increased throughput.
    
    Flow:
    File added → FileWatcher detects → Kafka event published → PrefectFlowConsumer triggers flow
    → Document processed → Saved to data/documents/processed/ → Downstream events published
    """
    
    def __init__(
        self, 
        watch_directory: Optional[str] = None,
        num_prefect_consumers: int = 1,
        consumer_group_id: str = "document_processors"
    ):
        """
        Initialize the document processing orchestrator.
        
        Args:
            watch_directory: Directory to watch for new documents (optional)
            num_prefect_consumers: Number of Prefect consumer instances for load balancing
            consumer_group_id: Kafka consumer group ID for load balancing
        """
        # Store scaling configuration
        self.num_prefect_consumers = num_prefect_consumers
        self.consumer_group_id = consumer_group_id
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize settings
        self.settings = get_settings()
        
        # Set up watch directory
        if watch_directory:
            self.watch_directory = Path(watch_directory)
        else:
            self.watch_directory = Path("data") / "documents" / "raw"
        
        self.watch_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.file_watcher = FileWatcherService(str(self.watch_directory))
        
        # Initialize multiple Prefect consumers for load balancing
        self.prefect_consumers = []
        for i in range(num_prefect_consumers):
            consumer = PrefectFlowConsumer(
                group_id=consumer_group_id,
                instance_id=f"consumer_{i}"
            )
            self.prefect_consumers.append(consumer)
        
        # Threading control
        self.consumer_threads = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎛️ DocumentProcessingOrchestrator initialized")
        self.logger.info(f"📂 Watching directory: {self.watch_directory}")
        self.logger.info(f"🏭 Prefect consumers: {num_prefect_consumers} (group: {consumer_group_id})")
        
    def start(self) -> None:
        """
        Start the complete document processing pipeline.
        
        This starts both the file watcher and the Prefect flow consumer
        in coordinated threads for automated document processing.
        """
        self.logger.info("🚀 Starting Document Processing Orchestrator")
        self.logger.info("=" * 60)
        
        try:
            # Ensure data directories exist
            self._ensure_directories()
            
            # Start Prefect flow consumers in background threads
            self.logger.info(f"🏭 Starting {self.num_prefect_consumers} Prefect Flow Consumer threads...")
            for i, consumer in enumerate(self.prefect_consumers):
                thread = threading.Thread(
                    target=self._run_consumer_thread,
                    args=(consumer, i),
                    name=f"PrefectFlowConsumer_{i}",
                    daemon=False
                )
                thread.start()
                self.consumer_threads.append(thread)
                
            # Give consumers time to initialize
            time.sleep(2)
            
            # Start file watcher in main thread
            self.logger.info("👁️ Starting File Watcher Service...")
            self.file_watcher.start()
            
            # Mark as running
            self.running = True
            
            self.logger.info("✅ Document Processing Orchestrator is running!")
            self.logger.info("📂 Drop files in: " + str(self.watch_directory))
            self.logger.info("📁 Processed files will appear in: data/documents/processed/")
            self.logger.info(f"⚖️ Load balancing: {self.num_prefect_consumers} consumers in group '{self.consumer_group_id}'")
            self.logger.info("🔄 Pipeline: File Detection → Prefect Flow → Vision AI → Structured Storage → Kafka Events")
            self.logger.info("=" * 60)
            
            # Keep main thread alive and handle shutdown gracefully
            self._run_main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start orchestrator: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the orchestrator and all services gracefully."""
        self.logger.info("🛑 Stopping Document Processing Orchestrator...")
        
        try:
            # Set shutdown flag
            self.running = False
            self.shutdown_event.set()
            
            # Stop file watcher
            if self.file_watcher.is_running():
                self.logger.info("🛑 Stopping file watcher...")
                self.file_watcher.stop()
            
            # Stop consumer threads
            if self.consumer_threads:
                self.logger.info(f"🛑 Stopping {len(self.consumer_threads)} Prefect flow consumers...")
                
                # Stop all consumers
                for i, consumer in enumerate(self.prefect_consumers):
                    try:
                        consumer.stop_consuming()
                        self.logger.info(f"✅ Consumer_{i} stopped")
                    except Exception as e:
                        self.logger.error(f"❌ Error stopping Consumer_{i}: {e}")
                
                # Wait for all consumer threads to finish
                for i, thread in enumerate(self.consumer_threads):
                    if thread.is_alive():
                        self.logger.info(f"⏳ Waiting for Consumer_{i} thread to finish...")
                        thread.join(timeout=10)
                        if thread.is_alive():
                            self.logger.warning(f"⚠️ Consumer_{i} thread didn't stop within timeout")
            
            self.logger.info("✅ Document Processing Orchestrator stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during orchestrator shutdown: {e}")
    
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        consumers_alive = all(
            thread.is_alive() for thread in self.consumer_threads
        ) if self.consumer_threads else False
        
        return (
            self.running and 
            self.file_watcher.is_running() and
            consumers_alive
        )
    
    def get_status(self) -> dict:
        """Get status of all orchestrator components."""
        consumer_statuses = [
            {
                "thread_name": thread.name,
                "alive": thread.is_alive(),
                "instance_id": consumer.instance_id
            }
            for thread, consumer in zip(self.consumer_threads, self.prefect_consumers)
        ]
        
        return {
            "orchestrator_running": self.running,
            "file_watcher_running": self.file_watcher.is_running(),
            "scaling_config": {
                "num_prefect_consumers": self.num_prefect_consumers,
                "consumer_group_id": self.consumer_group_id
            },
            "consumer_threads": consumer_statuses,
            "watch_directory": str(self.watch_directory),
            "processed_directory": str(Path("data") / "documents" / "processed")
        }
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            self.watch_directory,  # Raw documents
            Path("data") / "documents" / "processed",  # Processed documents
            Path("logs") / "pipelines",  # Log directories
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"📁 Ensured directory exists: {directory}")
    
    def _run_consumer_thread(self, consumer: PrefectFlowConsumer, consumer_index: int) -> None:
        """Run a Prefect flow consumer in a background thread."""
        try:
            self.logger.info(f"🎯 Prefect Flow Consumer_{consumer_index} thread started")
            consumer.start_consuming()
            
        except Exception as e:
            self.logger.error(f"❌ Prefect Flow Consumer_{consumer_index} thread error: {e}")
            
        finally:
            self.logger.info(f"🔚 Prefect Flow Consumer_{consumer_index} thread finished")
    
    def _run_main_loop(self) -> None:
        """Run the main orchestrator loop."""
        try:
            # Keep running until shutdown signal
            while self.running and not self.shutdown_event.is_set():
                time.sleep(1)
                
                # Check if components are still healthy
                if not self.file_watcher.is_running():
                    self.logger.error("❌ File watcher stopped unexpectedly")
                    break
                    
                # Check if any consumer threads stopped unexpectedly
                dead_consumers = [
                    i for i, thread in enumerate(self.consumer_threads) 
                    if not thread.is_alive()
                ]
                
                if dead_consumers:
                    self.logger.error(f"❌ Consumer threads stopped unexpectedly: {dead_consumers}")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Orchestrator interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Main loop error: {e}")


def setup_signal_handlers(orchestrator: DocumentProcessingOrchestrator) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, shutting down...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function for standalone execution."""
    print("🎛️ Document Processing Orchestrator")
    print("=" * 50)
    print("🚀 Starting automated document processing pipeline...")
    print("📂 Monitors: data/documents/raw/")
    print("📁 Outputs: data/documents/processed/")
    print("🔄 Pipeline: File Detection → Prefect → Vision AI → Storage → Kafka")
    print("=" * 50)
    print("📖 Usage examples:")
    print("   • Single consumer:  orchestrator = DocumentProcessingOrchestrator()")
    print("   • Scaled consumers: orchestrator = DocumentProcessingOrchestrator(num_prefect_consumers=3)")
    print("=" * 50)
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize orchestrator with scaling example (2 consumers)
    orchestrator = DocumentProcessingOrchestrator(
        watch_directory="data/documents/raw",
        num_prefect_consumers=3,
        consumer_group_id="scaled_document_processors"
    )
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers(orchestrator)
    
    try:
        # Start the orchestrator (blocking)
        orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)
        
    finally:
        # Ensure clean shutdown
        orchestrator.stop()
        print("✅ Service shutdown complete")


if __name__ == "__main__":
    main()