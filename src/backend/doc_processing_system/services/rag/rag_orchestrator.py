"""
RAG Processing Orchestrator - Configurable multi-stage consumer runner.
Coordinates independent RAG stage consumers for scalable document processing.
"""
import logging
import signal
import sys
import threading
import time
from typing import Optional, Dict, List
from ...messaging.rag_pipeline.chunking_consumer import ChunkingConsumer
from ...messaging.rag_pipeline.embedding_consumer import EmbeddingConsumer
from ...messaging.rag_pipeline.storage_consumer import StorageConsumer
from ...config.settings import get_settings


class RAGOrchestrator:
    """
    Orchestrates the complete decoupled RAG processing pipeline.
    
    Components:
    1. Chunking Consumers - Listen to document-available → publish chunking-complete
    2. Embedding Consumers - Listen to chunking-complete → publish embedding-ready  
    3. Storage Consumers - Listen to embedding-ready → publish ingestion-complete
    
    Supports independent scaling of each stage for optimal resource utilization.
    
    Flow:
    document-available → ChunkingConsumer → chunking-complete → EmbeddingConsumer 
    → embedding-ready → StorageConsumer → ingestion-complete
    """
    
    def __init__(
        self,
        num_chunking_consumers: int = 1,
        num_embedding_consumers: int = 1,
        num_storage_consumers: int = 1,
        chunking_group_id: str = "rag_chunking_group",
        embedding_group_id: str = "rag_embedding_group", 
        storage_group_id: str = "rag_storage_group"
    ):
        """
        Initialize the RAG processing orchestrator.
        
        Args:
            num_chunking_consumers: Number of chunking consumer instances
            num_embedding_consumers: Number of embedding consumer instances  
            num_storage_consumers: Number of storage consumer instances
            chunking_group_id: Kafka consumer group ID for chunking consumers
            embedding_group_id: Kafka consumer group ID for embedding consumers
            storage_group_id: Kafka consumer group ID for storage consumers
        """
        # Store scaling configuration
        self.num_chunking_consumers = num_chunking_consumers
        self.num_embedding_consumers = num_embedding_consumers
        self.num_storage_consumers = num_storage_consumers
        self.chunking_group_id = chunking_group_id
        self.embedding_group_id = embedding_group_id
        self.storage_group_id = storage_group_id
        
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
        
        # Initialize consumer instances
        self.chunking_consumers: List[ChunkingConsumer] = []
        self.embedding_consumers: List[EmbeddingConsumer] = []
        self.storage_consumers: List[StorageConsumer] = []
        
        # Create consumer instances with detailed logging
        self.logger.info(f"🔧 Creating {num_chunking_consumers} chunking consumers...")
        for i in range(num_chunking_consumers):
            try:
                consumer = ChunkingConsumer(group_id=chunking_group_id)
                consumer.instance_id = f"chunking_{i}"
                self.chunking_consumers.append(consumer)
                self.logger.info(f"✅ Created chunking consumer {i}: {consumer.instance_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to create chunking consumer {i}: {e}")
                raise
            
        self.logger.info(f"🔢 Creating {num_embedding_consumers} embedding consumers...")
        for i in range(num_embedding_consumers):
            try:
                consumer = EmbeddingConsumer(group_id=embedding_group_id)
                consumer.instance_id = f"embedding_{i}"
                self.embedding_consumers.append(consumer)
                self.logger.info(f"✅ Created embedding consumer {i}: {consumer.instance_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to create embedding consumer {i}: {e}")
                raise
            
        self.logger.info(f"🗄️ Creating {num_storage_consumers} storage consumers...")
        for i in range(num_storage_consumers):
            try:
                consumer = StorageConsumer(group_id=storage_group_id)
                consumer.instance_id = f"storage_{i}"
                self.storage_consumers.append(consumer)
                self.logger.info(f"✅ Created storage consumer {i}: {consumer.instance_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to create storage consumer {i}: {e}")
                raise
        
        # Threading control
        self.consumer_threads: List[threading.Thread] = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎯 RAG Processing Orchestrator initialized")
        self.logger.info(f"🔧 Chunking consumers: {num_chunking_consumers} (group: {chunking_group_id})")
        self.logger.info(f"🔢 Embedding consumers: {num_embedding_consumers} (group: {embedding_group_id})")
        self.logger.info(f"🗄️ Storage consumers: {num_storage_consumers} (group: {storage_group_id})")
    
    def start(self) -> None:
        """
        Start the complete RAG processing pipeline.
        
        This starts all consumer stages in coordinated threads for
        scalable, decoupled RAG document processing.
        """
        self.logger.info("🚀 Starting RAG Processing Orchestrator")
        self.logger.info("=" * 60)
        
        try:
            # Start chunking consumers
            self.logger.info(f"🔧 Starting {self.num_chunking_consumers} Chunking Consumer threads...")
            for i, consumer in enumerate(self.chunking_consumers):
                try:
                    thread = threading.Thread(
                        target=self._run_consumer_thread,
                        args=(consumer, f"Chunking_{i}"),
                        name=f"ChunkingConsumer_{i}",
                        daemon=False
                    )
                    thread.start()
                    self.consumer_threads.append(thread)
                    self.logger.info(f"🏃 Started chunking thread {i}: {thread.name}")
                    time.sleep(0.5)  # Small delay between thread starts
                except Exception as e:
                    self.logger.error(f"❌ Failed to start chunking thread {i}: {e}")
                    raise
            
            # Start embedding consumers
            self.logger.info(f"🔢 Starting {self.num_embedding_consumers} Embedding Consumer threads...")
            for i, consumer in enumerate(self.embedding_consumers):
                try:
                    thread = threading.Thread(
                        target=self._run_consumer_thread,
                        args=(consumer, f"Embedding_{i}"),
                        name=f"EmbeddingConsumer_{i}",
                        daemon=False
                    )
                    thread.start()
                    self.consumer_threads.append(thread)
                    self.logger.info(f"🏃 Started embedding thread {i}: {thread.name}")
                    time.sleep(0.5)  # Small delay between thread starts
                except Exception as e:
                    self.logger.error(f"❌ Failed to start embedding thread {i}: {e}")
                    raise
            
            # Start storage consumers
            self.logger.info(f"🗄️ Starting {self.num_storage_consumers} Storage Consumer threads...")
            for i, consumer in enumerate(self.storage_consumers):
                try:
                    thread = threading.Thread(
                        target=self._run_consumer_thread,
                        args=(consumer, f"Storage_{i}"),
                        name=f"StorageConsumer_{i}",
                        daemon=False
                    )
                    thread.start()
                    self.consumer_threads.append(thread)
                    self.logger.info(f"🏃 Started storage thread {i}: {thread.name}")
                    time.sleep(0.5)  # Small delay between thread starts
                except Exception as e:
                    self.logger.error(f"❌ Failed to start storage thread {i}: {e}")
                    raise
            
            # Give all consumers time to initialize
            self.logger.info("⏳ Waiting for all consumers to initialize...")
            time.sleep(5)
            
            # Check that all threads are still alive after initialization
            alive_threads = [t.name for t in self.consumer_threads if t.is_alive()]
            dead_threads = [t.name for t in self.consumer_threads if not t.is_alive()]
            
            self.logger.info(f"✅ Threads alive: {len(alive_threads)}/{len(self.consumer_threads)}")
            if alive_threads:
                self.logger.info(f"🟢 Alive: {alive_threads}")
            if dead_threads:
                self.logger.error(f"🔴 Dead: {dead_threads}")
                raise Exception(f"Some consumer threads failed to start: {dead_threads}")
            
            # Mark as running
            self.running = True
            
            self.logger.info("✅ RAG Processing Orchestrator is running!")
            self.logger.info("🔄 Pipeline Flow:")
            self.logger.info("   📄 document-available → 🔧 Chunking → chunking-complete")
            self.logger.info("   📊 chunking-complete → 🔢 Embedding → embedding-ready")
            self.logger.info("   🔗 embedding-ready → 🗄️ Storage → ingestion-complete")
            self.logger.info(f"⚖️ Scaling: {self.num_chunking_consumers}+{self.num_embedding_consumers}+{self.num_storage_consumers} consumers")
            self.logger.info("=" * 60)
            
            # Keep main thread alive and handle shutdown gracefully
            self._run_main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start RAG orchestrator: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the orchestrator and all consumers gracefully."""
        self.logger.info("🛑 Stopping RAG Processing Orchestrator...")
        
        try:
            # Set shutdown flag
            self.running = False
            self.shutdown_event.set()
            
            # Stop all consumers by category
            all_consumers = [
                ("Chunking", self.chunking_consumers),
                ("Embedding", self.embedding_consumers), 
                ("Storage", self.storage_consumers)
            ]
            
            for consumer_type, consumers in all_consumers:
                if consumers:
                    self.logger.info(f"🛑 Stopping {len(consumers)} {consumer_type} consumers...")
                    for i, consumer in enumerate(consumers):
                        try:
                            consumer.stop_consuming()
                            self.logger.info(f"✅ {consumer_type}_{i} stopped")
                        except Exception as e:
                            self.logger.error(f"❌ Error stopping {consumer_type}_{i}: {e}")
            
            # Wait for all consumer threads to finish
            if self.consumer_threads:
                self.logger.info(f"⏳ Waiting for {len(self.consumer_threads)} threads to finish...")
                for thread in self.consumer_threads:
                    if thread.is_alive():
                        thread.join(timeout=10)
                        if thread.is_alive():
                            self.logger.warning(f"⚠️ Thread {thread.name} didn't stop within timeout")
                        else:
                            self.logger.info(f"✅ Thread {thread.name} finished")
            
            self.logger.info("✅ RAG Processing Orchestrator stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during RAG orchestrator shutdown: {e}")
    
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        threads_alive = all(
            thread.is_alive() for thread in self.consumer_threads
        ) if self.consumer_threads else False
        
        return self.running and threads_alive
    
    def get_status(self) -> dict:
        """Get status of all orchestrator components."""
        def get_consumer_statuses(consumers, consumer_type):
            return [
                {
                    "instance_id": getattr(consumer, 'instance_id', f"{consumer_type}_{i}"),
                    "group_id": consumer.group_id,
                    "subscribed_topics": consumer.get_subscribed_topics()
                }
                for i, consumer in enumerate(consumers)
            ]
        
        thread_statuses = [
            {
                "thread_name": thread.name,
                "alive": thread.is_alive()
            }
            for thread in self.consumer_threads
        ]
        
        return {
            "orchestrator_running": self.running,
            "total_threads": len(self.consumer_threads),
            "threads_alive": sum(1 for thread in self.consumer_threads if thread.is_alive()),
            "scaling_config": {
                "num_chunking_consumers": self.num_chunking_consumers,
                "num_embedding_consumers": self.num_embedding_consumers,
                "num_storage_consumers": self.num_storage_consumers,
                "chunking_group_id": self.chunking_group_id,
                "embedding_group_id": self.embedding_group_id,
                "storage_group_id": self.storage_group_id
            },
            "consumers": {
                "chunking": get_consumer_statuses(self.chunking_consumers, "chunking"),
                "embedding": get_consumer_statuses(self.embedding_consumers, "embedding"),
                "storage": get_consumer_statuses(self.storage_consumers, "storage")
            },
            "thread_details": thread_statuses
        }
    
    def _run_consumer_thread(self, consumer, consumer_name: str) -> None:
        """Run a consumer in a background thread."""
        try:
            self.logger.info(f"🎯 {consumer_name} Consumer thread started")
            self.logger.info(f"🔗 {consumer_name} subscribing to topics: {consumer.get_subscribed_topics()}")
            self.logger.info(f"👥 {consumer_name} consumer group: {consumer.group_id}")
            
            # Run blocking consume loop directly instead of start_consuming()
            # which creates its own thread and returns immediately
            self.logger.info(f"🏃 {consumer_name} starting blocking consumption loop...")
            
            # Direct blocking consumption loop
            while not self.shutdown_event.is_set():
                try:
                    # Call consume_events directly for blocking behavior
                    consumer.consume_events()
                except KeyboardInterrupt:
                    self.logger.info(f"🛑 {consumer_name} consumption interrupted")
                    break
                except Exception as e:
                    self.logger.error(f"❌ {consumer_name} consumption error: {e}")
                    # Continue consuming after error
                    import time
                    time.sleep(1)
            
        except KeyboardInterrupt:
            self.logger.info(f"🛑 {consumer_name} Consumer thread interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ {consumer_name} Consumer thread error: {e}")
            self.logger.exception(f"Full {consumer_name} exception details:")
            # Re-raise to make thread failure more visible
            raise
        finally:
            self.logger.info(f"🔚 {consumer_name} Consumer thread finished")
    
    def _run_main_loop(self) -> None:
        """Run the main orchestrator loop."""
        try:
            # Keep running until shutdown signal
            while self.running and not self.shutdown_event.is_set():
                time.sleep(2)
                
                # Detailed thread health check
                dead_threads = []
                thread_details = []
                
                for thread in self.consumer_threads:
                    is_alive = thread.is_alive()
                    thread_info = {
                        "name": thread.name,
                        "alive": is_alive,
                        "daemon": thread.daemon,
                        "ident": thread.ident
                    }
                    thread_details.append(thread_info)
                    
                    if not is_alive:
                        dead_threads.append(thread.name)
                
                if dead_threads:
                    self.logger.error(f"❌ Consumer threads stopped unexpectedly: {dead_threads}")
                    self.logger.error("📊 Thread status details:")
                    for info in thread_details:
                        status = "🟢 ALIVE" if info["alive"] else "🔴 DEAD"
                        self.logger.error(f"   {status} {info['name']} (ID: {info['ident']}, Daemon: {info['daemon']})")
                    
                    # Log potential causes
                    self.logger.error("🔍 Potential causes:")
                    self.logger.error("   • Kafka connection issues")
                    self.logger.error("   • Import/dependency errors") 
                    self.logger.error("   • Configuration problems")
                    self.logger.error("   • Resource constraints")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 RAG Orchestrator interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Main loop error: {e}")
            self.logger.exception("Full main loop exception details:")


def setup_signal_handlers(orchestrator: RAGOrchestrator) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, shutting down RAG orchestrator...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function for standalone execution."""
    print("🎯 RAG Processing Orchestrator")
    print("=" * 50)
    print("🚀 Starting scalable RAG processing pipeline...")
    print("📄 Listens to: document-available events")
    print("📤 Publishes: chunking-complete → embedding-ready → ingestion-complete")
    print("🔄 Pipeline: Chunking → Embedding → ChromaDB Storage")
    print("=" * 50)
    print("📖 Scaling examples:")
    print("   • Balanced:     RAGOrchestrator(2, 2, 1)")
    print("   • Chunking-heavy: RAGOrchestrator(4, 2, 1)")
    print("   • Embedding-heavy: RAGOrchestrator(2, 4, 1)")
    print("=" * 50)
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize orchestrator with example scaling configuration
    orchestrator = RAGOrchestrator(
        num_chunking_consumers=2,    # CPU-intensive semantic chunking
        num_embedding_consumers=2,   # GPU/memory-intensive embedding generation
        num_storage_consumers=1,     # I/O-intensive ChromaDB operations
        chunking_group_id="scaled_rag_chunking",
        embedding_group_id="scaled_rag_embedding", 
        storage_group_id="scaled_rag_storage"
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
        print("✅ RAG Service shutdown complete")


if __name__ == "__main__":
    main()