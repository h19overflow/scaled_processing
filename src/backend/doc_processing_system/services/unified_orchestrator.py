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

# Legacy document processing orchestrator removed - now handled by ChonkieProcessor directly
from .rag.rag_orchestrator import RAGOrchestrator
from ..config.settings import get_settings


class UnifiedOrchestrator:
    """
    Simplified orchestrator that focuses on RAG processing with Chonkie integration.
    
    Simplified Flow:
    document-available event → ChonkieRAGOrchestrator → Unified Pipeline → Weaviate
    
    Document processing is now handled directly by ChonkieProcessor/FileProcessingConsumer.
    """
    
    def __init__(
        self,
        # Chonkie RAG Processing Configuration  
        num_rag_consumers: int = 2,
        rag_group: str = "unified_chonkie_rag"
    ):
        """
        Initialize the simplified Chonkie RAG orchestrator.
        
        Args:
            num_rag_consumers: Number of unified Chonkie RAG consumers
            rag_group: Kafka consumer group for Chonkie RAG processing
        """
        # Store simplified configuration
        self.config = {
            "chonkie_rag_processing": {
                "num_rag_consumers": num_rag_consumers,
                "rag_group": rag_group
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
        
        # Initialize simplified RAG orchestrator only
        self.rag_orchestrator = RAGOrchestrator(
            num_rag_consumers=self.config["chonkie_rag_processing"]["num_rag_consumers"],
            rag_group_id=self.config["chonkie_rag_processing"]["rag_group"]
        )
        
        # Threading control
        self.orchestrator_threads = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎼 Simplified Chonkie Orchestrator initialized")
        self.logger.info(f"🎯 Chonkie RAG Pipeline: {num_rag_consumers} unified consumers")
        self.logger.info("📄 Document processing handled by ChonkieProcessor/FileProcessingConsumer")
    
    def start(self) -> None:
        """
        Start the simplified Chonkie RAG processing system.
        
        Starts the unified Chonkie RAG orchestrator for high-performance
        document processing with chunking + embedding + storage.
        """
        self.logger.info("🚀 Starting Simplified Chonkie RAG System")
        self.logger.info("=" * 60)
        
        try:
            # Ensure directories exist
            self._ensure_directories()
            
            # Start RAG Processing Orchestrator directly (no document orchestrator needed)
            self.logger.info("🎯 Starting Chonkie RAG Processing Orchestrator...")
            self.rag_orchestrator.start()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Chonkie RAG system: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the simplified orchestrator and RAG processing gracefully."""
        self.logger.info("🛑 Stopping Simplified Chonkie RAG System...")
        
        try:
            # Set shutdown flag
            self.running = False
            self.shutdown_event.set()
            
            # Stop RAG orchestrator
            self.logger.info("🛑 Stopping Chonkie RAG Processing Orchestrator...")
            try:
                self.rag_orchestrator.stop()
                self.logger.info("✅ Chonkie RAG Processing Orchestrator stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping Chonkie RAG Orchestrator: {e}")
            
            self.logger.info("✅ Simplified Chonkie RAG System stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during orchestrator shutdown: {e}")
    
    def is_running(self) -> bool:
        """Check if the simplified orchestrator is running."""
        return self.running and self.rag_orchestrator.is_running()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of simplified system components."""
        return {
            "simplified_orchestrator_running": self.running,
            "configuration": self.config,
            "chonkie_rag_processing": self.rag_orchestrator.get_status(),
            "system_health": {
                "rag_pipeline_healthy": self.rag_orchestrator.is_running(),
                "overall_healthy": self.is_running()
            }
        }
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            Path("logs/orchestrators")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"📁 Ensured directory exists: {directory}")
    


def setup_signal_handlers(orchestrator: UnifiedOrchestrator) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, shutting down Chonkie RAG system...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function for standalone execution."""
    print("🎯 Simplified Chonkie RAG System")
    print("=" * 50)
    print("🚀 Unified high-performance RAG processing pipeline")
    print("📨 document-available → ChonkieRAG → Weaviate Storage")
    print("=" * 50)
    print("⚖️ Scaling Examples:")
    print("   • Light load:    UnifiedOrchestrator(rag=1)")
    print("   • Balanced:      UnifiedOrchestrator(rag=2)")
    print("   • Heavy load:    UnifiedOrchestrator(rag=4)")
    print("=" * 50)
    print("📄 Document processing handled by ChonkieProcessor/FileProcessingConsumer")
    print("🗄️ Vector search ready in Weaviate collections")
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize simplified orchestrator 
    orchestrator = UnifiedOrchestrator(
        # Chonkie RAG Processing Pipeline  
        num_rag_consumers=2,    # Unified Chonkie consumers (chunking+embedding+storage)
        rag_group="unified_chonkie_rag"
    )
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers(orchestrator)
    
    try:
        # Start the simplified Chonkie RAG system (blocking)
        orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        
    except Exception as e:
        print(f"❌ System error: {e}")
        sys.exit(1)
        
    finally:
        # Ensure clean shutdown
        orchestrator.stop()
        print("✅ Chonkie RAG System shutdown complete")


if __name__ == "__main__":
    main()