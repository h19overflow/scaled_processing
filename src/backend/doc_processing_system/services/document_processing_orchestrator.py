"""
Document Processing Orchestrator - Unified service runner.
Coordinates FileWatcherService and PrefectFlowConsumer for automated document processing.
"""

import asyncio
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .file_watcher import FileWatcherService
from .prefect_flow_consumer import PrefectFlowConsumer
from ..config.settings import get_settings


class DocumentProcessingOrchestrator:
    """
    Orchestrates the complete automated document processing pipeline.
    
    Components:
    1. FileWatcherService - Monitors data/documents/raw/ for new files
    2. PrefectFlowConsumer - Consumes file-detected events and triggers Prefect flows
    
    Flow:
    File added → FileWatcher detects → Kafka event published → PrefectFlowConsumer triggers flow
    → Document processed → Saved to data/documents/processed/ → Downstream events published
    """
    
    def __init__(self, watch_directory: Optional[str] = None):
        """
        Initialize the document processing orchestrator.
        
        Args:
            watch_directory: Directory to watch for new documents (optional)
        """
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
        self.prefect_consumer = PrefectFlowConsumer()
        
        # Threading control
        self.consumer_thread: Optional[threading.Thread] = None
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎛️ DocumentProcessingOrchestrator initialized")
        self.logger.info(f"📂 Watching directory: {self.watch_directory}")
        
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
            
            # Start Prefect flow consumer in background thread
            self.logger.info("🏭 Starting Prefect Flow Consumer thread...")
            self.consumer_thread = threading.Thread(
                target=self._run_consumer_thread,
                name="PrefectFlowConsumer",
                daemon=False
            )
            self.consumer_thread.start()
            
            # Give consumer time to initialize
            time.sleep(2)
            
            # Start file watcher in main thread
            self.logger.info("👁️ Starting File Watcher Service...")
            self.file_watcher.start()
            
            # Mark as running
            self.running = True
            
            self.logger.info("✅ Document Processing Orchestrator is running!")
            self.logger.info("📂 Drop files in: " + str(self.watch_directory))
            self.logger.info("📁 Processed files will appear in: data/documents/processed/")
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
            
            # Stop consumer thread
            if self.consumer_thread and self.consumer_thread.is_alive():
                self.logger.info("🛑 Stopping Prefect flow consumer...")
                self.prefect_consumer.stop_consuming()
                
                # Wait for consumer thread to finish (with timeout)
                self.consumer_thread.join(timeout=10)
                if self.consumer_thread.is_alive():
                    self.logger.warning("⚠️ Consumer thread didn't stop within timeout")
            
            self.logger.info("✅ Document Processing Orchestrator stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during orchestrator shutdown: {e}")
    
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        return (
            self.running and 
            self.file_watcher.is_running() and
            self.consumer_thread and 
            self.consumer_thread.is_alive()
        )
    
    def get_status(self) -> dict:
        """Get status of all orchestrator components."""
        return {
            "orchestrator_running": self.running,
            "file_watcher_running": self.file_watcher.is_running(),
            "consumer_thread_alive": self.consumer_thread.is_alive() if self.consumer_thread else False,
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
    
    def _run_consumer_thread(self) -> None:
        """Run the Prefect flow consumer in a background thread."""
        try:
            self.logger.info("🎯 Prefect Flow Consumer thread started")
            self.prefect_consumer.start_consuming()
            
        except Exception as e:
            self.logger.error(f"❌ Prefect Flow Consumer thread error: {e}")
            
        finally:
            self.logger.info("🔚 Prefect Flow Consumer thread finished")
    
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
                    
                if self.consumer_thread and not self.consumer_thread.is_alive():
                    self.logger.error("❌ Prefect consumer thread stopped unexpectedly")
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
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize orchestrator
    orchestrator = DocumentProcessingOrchestrator(watch_directory="data/documents/raw")
    
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