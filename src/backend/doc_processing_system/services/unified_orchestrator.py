"""
Unified Document Processing System - Master Orchestrator

Coordinates both document processing and RAG processing pipelines
for complete end-to-end automated document analysis and storage.

Architecture:
1. Document Processing Pipeline: File Detection → Docling → Database
2. RAG Processing Pipeline: document-available → Chunking → Embedding → ChromaDB

Highly configurable scaling for optimal resource utilization.
"""
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .document_processing.document_processing_orchestrator import DocumentProcessingOrchestrator
from .rag.rag_orchestrator import RAGOrchestrator
from ..config.settings import get_settings


class UnifiedOrchestrator:
    """
    Master orchestrator that coordinates both document processing and RAG pipelines.
    
    Complete Flow:
    File Added → DocumentOrchestrator → Docling Processing → Database Storage 
    → document-available event → RAGOrchestrator → Chunking → Embedding → ChromaDB
    
    Supports independent scaling of each pipeline stage for maximum throughput.
    """
    
    def __init__(
        self,
        # Document Processing Configuration
        watch_directory: Optional[str] = None,
        num_document_consumers: int = 2,
        document_consumer_group: str = "unified_document_processors",
        
        # RAG Processing Configuration  
        num_chunking_consumers: int = 2,
        num_embedding_consumers: int = 2,
        num_storage_consumers: int = 1,
        chunking_group: str = "unified_rag_chunking",
        embedding_group: str = "unified_rag_embedding",
        storage_group: str = "unified_rag_storage"
    ):
        """
        Initialize the unified document processing system.
        
        Args:
            watch_directory: Directory to monitor for new files
            num_document_consumers: Number of document processing consumers
            document_consumer_group: Kafka consumer group for document processors
            num_chunking_consumers: Number of chunking consumers
            num_embedding_consumers: Number of embedding consumers  
            num_storage_consumers: Number of storage consumers
            chunking_group: Kafka consumer group for chunking
            embedding_group: Kafka consumer group for embedding
            storage_group: Kafka consumer group for storage
        """
        # Store configuration
        self.config = {
            "document_processing": {
                "watch_directory": watch_directory or "data/documents/raw",
                "num_consumers": num_document_consumers,
                "consumer_group": document_consumer_group
            },
            "rag_processing": {
                "num_chunking_consumers": num_chunking_consumers,
                "num_embedding_consumers": num_embedding_consumers,
                "num_storage_consumers": num_storage_consumers,
                "chunking_group": chunking_group,
                "embedding_group": embedding_group,
                "storage_group": storage_group
            }
        }
        
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
        
        # Initialize orchestrators
        self.document_orchestrator = DocumentProcessingOrchestrator(
            watch_directory=self.config["document_processing"]["watch_directory"],
            num_prefect_consumers=self.config["document_processing"]["num_consumers"],
            consumer_group_id=self.config["document_processing"]["consumer_group"]
        )
        
        self.rag_orchestrator = RAGOrchestrator(
            num_chunking_consumers=self.config["rag_processing"]["num_chunking_consumers"],
            num_embedding_consumers=self.config["rag_processing"]["num_embedding_consumers"],
            num_storage_consumers=self.config["rag_processing"]["num_storage_consumers"],
            chunking_group_id=self.config["rag_processing"]["chunking_group"],
            embedding_group_id=self.config["rag_processing"]["embedding_group"],
            storage_group_id=self.config["rag_processing"]["storage_group"]
        )
        
        # Threading control
        self.orchestrator_threads = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎼 Unified Orchestrator initialized")
        self.logger.info(f"📂 Document Pipeline: {num_document_consumers} consumers (watching: {self.config['document_processing']['watch_directory']})")
        self.logger.info(f"🎯 RAG Pipeline: {num_chunking_consumers}+{num_embedding_consumers}+{num_storage_consumers} consumers")
    
    def start(self) -> None:
        """
        Start the complete unified document processing system.
        
        Starts both document processing and RAG processing orchestrators
        in coordinated threads for end-to-end automated document analysis.
        """
        self.logger.info("🚀 Starting Unified Document Processing System")
        self.logger.info("=" * 80)
        
        try:
            # Ensure directories exist
            self._ensure_directories()
            
            # Start Document Processing Orchestrator in background thread
            self.logger.info("📄 Starting Document Processing Orchestrator thread...")
            doc_thread = threading.Thread(
                target=self._run_document_orchestrator,
                name="DocumentOrchestrator",
                daemon=False
            )
            doc_thread.start()
            self.orchestrator_threads.append(doc_thread)
            
            # Give document orchestrator time to initialize
            time.sleep(3)
            
            # Start RAG Processing Orchestrator in background thread
            self.logger.info("🎯 Starting RAG Processing Orchestrator thread...")
            rag_thread = threading.Thread(
                target=self._run_rag_orchestrator,
                name="RAGOrchestrator",
                daemon=False
            )
            rag_thread.start()
            self.orchestrator_threads.append(rag_thread)
            
            # Give RAG orchestrator time to initialize
            time.sleep(3)
            
            # Mark as running
            self.running = True
            
            self.logger.info("✅ Unified Document Processing System is running!")
            self.logger.info("🔄 Complete Pipeline Flow:")
            self.logger.info("   📁 File Drop → 👁️ FileWatcher → 🔄 Docling → 💾 Database")
            self.logger.info("   📨 document-available → 🔧 Chunking → 🔢 Embedding → 🗄️ ChromaDB")
            self.logger.info(f"📂 Drop files in: {self.config['document_processing']['watch_directory']}")
            self.logger.info("📁 Processed files: data/documents/processed/")
            self.logger.info("🗄️ Vector storage: ChromaDB collections")
            self.logger.info("⚖️ Scaling Configuration:")
            self.logger.info(f"   📄 Document: {self.config['document_processing']['num_consumers']} consumers")
            self.logger.info(f"   🎯 RAG: {self.config['rag_processing']['num_chunking_consumers']}+{self.config['rag_processing']['num_embedding_consumers']}+{self.config['rag_processing']['num_storage_consumers']} consumers")
            self.logger.info("=" * 80)
            
            # Keep main thread alive and monitor health
            self._run_main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start unified orchestrator: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the unified orchestrator and all sub-orchestrators gracefully."""
        self.logger.info("🛑 Stopping Unified Document Processing System...")
        
        try:
            # Set shutdown flag
            self.running = False
            self.shutdown_event.set()
            
            # Stop orchestrators
            self.logger.info("🛑 Stopping Document Processing Orchestrator...")
            try:
                self.document_orchestrator.stop()
                self.logger.info("✅ Document Processing Orchestrator stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping Document Orchestrator: {e}")
            
            self.logger.info("🛑 Stopping RAG Processing Orchestrator...")
            try:
                self.rag_orchestrator.stop()
                self.logger.info("✅ RAG Processing Orchestrator stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping RAG Orchestrator: {e}")
            
            # Wait for orchestrator threads to finish
            if self.orchestrator_threads:
                self.logger.info("⏳ Waiting for orchestrator threads to finish...")
                for thread in self.orchestrator_threads:
                    if thread.is_alive():
                        thread.join(timeout=15)
                        if thread.is_alive():
                            self.logger.warning(f"⚠️ Thread {thread.name} didn't stop within timeout")
                        else:
                            self.logger.info(f"✅ Thread {thread.name} finished")
            
            self.logger.info("✅ Unified Document Processing System stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during unified orchestrator shutdown: {e}")
    
    def is_running(self) -> bool:
        """Check if the unified orchestrator is running."""
        return (
            self.running and
            self.document_orchestrator.is_running() and
            self.rag_orchestrator.is_running() and
            all(thread.is_alive() for thread in self.orchestrator_threads)
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all system components."""
        return {
            "unified_orchestrator_running": self.running,
            "configuration": self.config,
            "orchestrator_threads": [
                {
                    "name": thread.name,
                    "alive": thread.is_alive()
                }
                for thread in self.orchestrator_threads
            ],
            "document_processing": self.document_orchestrator.get_status(),
            "rag_processing": self.rag_orchestrator.get_status(),
            "system_health": {
                "document_pipeline_healthy": self.document_orchestrator.is_running(),
                "rag_pipeline_healthy": self.rag_orchestrator.is_running(),
                "overall_healthy": self.is_running()
            }
        }
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            Path(self.config["document_processing"]["watch_directory"]),
            Path("data/documents/processed"),
            Path("data/rag/chunks"),
            Path("data/rag/embeddings"),
            Path("logs/orchestrators")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"📁 Ensured directory exists: {directory}")
    
    def _run_document_orchestrator(self) -> None:
        """Run the document processing orchestrator in a background thread."""
        try:
            self.logger.info("📄 Document Processing Orchestrator thread started")
            self.document_orchestrator.start()
        except Exception as e:
            self.logger.error(f"❌ Document Processing Orchestrator thread error: {e}")
        finally:
            self.logger.info("🔚 Document Processing Orchestrator thread finished")
    
    def _run_rag_orchestrator(self) -> None:
        """Run the RAG processing orchestrator in a background thread."""
        try:
            self.logger.info("🎯 RAG Processing Orchestrator thread started")
            self.rag_orchestrator.start()
        except Exception as e:
            self.logger.error(f"❌ RAG Processing Orchestrator thread error: {e}")
        finally:
            self.logger.info("🔚 RAG Processing Orchestrator thread finished")
    
    def _run_main_loop(self) -> None:
        """Run the main unified orchestrator loop."""
        try:
            # Keep running until shutdown signal
            while self.running and not self.shutdown_event.is_set():
                time.sleep(5)
                
                # Health check
                if not self.document_orchestrator.is_running():
                    self.logger.error("❌ Document Processing Orchestrator stopped unexpectedly")
                    break
                    
                if not self.rag_orchestrator.is_running():
                    self.logger.error("❌ RAG Processing Orchestrator stopped unexpectedly")
                    break
                
                # Check orchestrator threads
                dead_threads = [
                    thread.name for thread in self.orchestrator_threads
                    if not thread.is_alive()
                ]
                
                if dead_threads:
                    self.logger.error(f"❌ Orchestrator threads stopped unexpectedly: {dead_threads}")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Unified Orchestrator interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Main loop error: {e}")


def setup_signal_handlers(orchestrator: UnifiedOrchestrator) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, shutting down unified system...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function for standalone execution."""
    print("🎼 Unified Document Processing System")
    print("=" * 60)
    print("🚀 Complete end-to-end document analysis pipeline")
    print("📂 File Detection → Document Processing → RAG Analysis → Vector Storage")
    print("=" * 60)
    print("⚖️ Scaling Examples:")
    print("   • Balanced:      UnifiedOrchestrator(doc=2, chunk=2, embed=2, store=1)")
    print("   • Document-heavy: UnifiedOrchestrator(doc=4, chunk=2, embed=1, store=1)")
    print("   • RAG-heavy:     UnifiedOrchestrator(doc=1, chunk=3, embed=3, store=2)")
    print("=" * 60)
    print("📁 Drop files in: data/documents/raw/")
    print("🗄️ Vector search ready in ChromaDB collections")
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize unified orchestrator with balanced scaling
    orchestrator = UnifiedOrchestrator(
        # Document Processing Pipeline
        watch_directory="data/documents/raw",
        num_document_consumers=2,
        document_consumer_group="unified_doc_processors",
        
        # RAG Processing Pipeline  
        num_chunking_consumers=2,    # CPU-intensive semantic processing
        num_embedding_consumers=2,   # GPU/memory-intensive embedding generation
        num_storage_consumers=1,     # I/O-intensive ChromaDB operations
        chunking_group="unified_chunking",
        embedding_group="unified_embedding",
        storage_group="unified_storage"
    )
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers(orchestrator)
    
    try:
        # Start the unified system (blocking)
        orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        
    except Exception as e:
        print(f"❌ System error: {e}")
        sys.exit(1)
        
    finally:
        # Ensure clean shutdown
        orchestrator.stop()
        print("✅ Unified System shutdown complete")


if __name__ == "__main__":
    main()