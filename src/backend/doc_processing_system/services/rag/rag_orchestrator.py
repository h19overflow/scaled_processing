"""
Chonkie RAG Processing Orchestrator - Unified single-stage consumer runner.
Coordinates Chonkie-based RAG consumers for scalable document processing with 2-33x performance improvement.
"""
import logging
import signal
import sys
import threading
import time
from typing import Optional, Dict, List
from ...pipelines.rag_processing.flows.rag_consumer import RagProcessingConsumer
from ...config.settings import get_settings


class RAGOrchestrator:
    """
    Orchestrates the unified Chonkie RAG processing pipeline.
    
    Simplified Architecture:
    - Single unified consumer type (RagProcessingConsumer) 
    - Direct Chonkie pipeline integration (chunking + embeddings + storage)
    - 2-33x performance improvement over legacy 5-stage pipeline
    
    Flow:
    document-available → RagProcessingConsumer → (Chonkie unified pipeline) → complete
    """
    
    def __init__(
        self,
        num_rag_consumers: int = 2,
        rag_group_id: str = "chonkie_rag_group"
    ):
        """
        Initialize the Chonkie RAG processing orchestrator.
        
        Args:
            num_rag_consumers: Number of unified RAG consumer instances
            rag_group_id: Kafka consumer group ID for RAG consumers
        """
        # Store simplified configuration
        self.num_rag_consumers = num_rag_consumers
        self.rag_group_id = rag_group_id
        
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
        
        # Initialize unified RAG consumer instances
        self.rag_consumers: List[RagProcessingConsumer] = []
        
        # Create consumer instances with detailed logging
        self.logger.info(f"🎯 Creating {num_rag_consumers} Chonkie RAG consumers...")
        for i in range(num_rag_consumers):
            try:
                consumer = RagProcessingConsumer(group_id=rag_group_id)
                consumer.instance_id = f"chonkie_rag_{i}"
                self.rag_consumers.append(consumer)
                self.logger.info(f"✅ Created Chonkie RAG consumer {i}: {consumer.instance_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to create Chonkie RAG consumer {i}: {e}")
                raise
        
        # Threading control
        self.consumer_threads: List[threading.Thread] = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        self.logger.info("🎯 Chonkie RAG Processing Orchestrator initialized")
        self.logger.info(f"🚀 Unified consumers: {num_rag_consumers} (group: {rag_group_id})")
        self.logger.info("⚡ Performance: 2-33x faster than legacy 5-stage pipeline")
    
    def start(self) -> None:
        """
        Start the complete Chonkie RAG processing pipeline.
        
        This starts unified RAG consumers in coordinated threads for
        high-performance document processing with Chonkie integration.
        """
        self.logger.info("🚀 Starting Chonkie RAG Processing Orchestrator")
        self.logger.info("=" * 60)
        
        try:
            # Start unified RAG consumers
            self.logger.info(f"🎯 Starting {self.num_rag_consumers} Chonkie RAG Consumer threads...")
            for i, consumer in enumerate(self.rag_consumers):
                try:
                    thread = threading.Thread(
                        target=self._run_consumer_thread,
                        args=(consumer, f"ChonkieRAG_{i}"),
                        name=f"ChonkieRAGConsumer_{i}",
                        daemon=False
                    )
                    thread.start()
                    self.consumer_threads.append(thread)
                    self.logger.info(f"🏃 Started Chonkie RAG thread {i}: {thread.name}")
                    time.sleep(0.5)  # Small delay between thread starts
                except Exception as e:
                    self.logger.error(f"❌ Failed to start Chonkie RAG thread {i}: {e}")
                    raise
            
            # Give all consumers time to initialize
            self.logger.info("⏳ Waiting for all Chonkie consumers to initialize...")
            time.sleep(3)
            
            # Check that all threads are still alive after initialization
            alive_threads = [t.name for t in self.consumer_threads if t.is_alive()]
            dead_threads = [t.name for t in self.consumer_threads if not t.is_alive()]
            
            self.logger.info(f"✅ Threads alive: {len(alive_threads)}/{len(self.consumer_threads)}")
            if alive_threads:
                self.logger.info(f"🟢 Alive: {alive_threads}")
            if dead_threads:
                self.logger.error(f"🔴 Dead: {dead_threads}")
                raise Exception(f"Some Chonkie consumer threads failed to start: {dead_threads}")
            
            # Mark as running
            self.running = True
            
            self.logger.info("✅ Chonkie RAG Processing Orchestrator is running!")
            self.logger.info("🔄 Unified Pipeline Flow:")
            self.logger.info("   📄 document-available → 🎯 ChonkieRAG → (chunking+embedding+storage) → complete")
            self.logger.info("   ⚡ Performance: 2-33x faster than legacy multi-stage pipeline")
            self.logger.info("   🗄️ Direct Weaviate storage (no intermediate JSON files)")
            self.logger.info(f"⚖️ Scaling: {self.num_rag_consumers} unified consumers")
            self.logger.info("=" * 60)
            
            # Keep main thread alive and handle shutdown gracefully
            self._run_main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Chonkie RAG orchestrator: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the orchestrator and all consumers gracefully."""
        self.logger.info("🛑 Stopping Chonkie RAG Processing Orchestrator...")
        
        try:
            # Set shutdown flag
            self.running = False
            self.shutdown_event.set()
            
            # Stop all Chonkie RAG consumers
            if self.rag_consumers:
                self.logger.info(f"🛑 Stopping {len(self.rag_consumers)} Chonkie RAG consumers...")
                for i, consumer in enumerate(self.rag_consumers):
                    try:
                        consumer.stop_consuming()
                        self.logger.info(f"✅ ChonkieRAG_{i} stopped")
                    except Exception as e:
                        self.logger.error(f"❌ Error stopping ChonkieRAG_{i}: {e}")
            
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
            
            self.logger.info("✅ Chonkie RAG Processing Orchestrator stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error during Chonkie RAG orchestrator shutdown: {e}")
    
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
            "orchestrator_type": "chonkie_unified",
            "performance_improvement": "2-33x vs legacy pipeline",
            "total_threads": len(self.consumer_threads),
            "threads_alive": sum(1 for thread in self.consumer_threads if thread.is_alive()),
            "scaling_config": {
                "num_rag_consumers": self.num_rag_consumers,
                "rag_group_id": self.rag_group_id,
                "pipeline_type": "unified_chonkie"
            },
            "consumers": {
                "chonkie_rag": get_consumer_statuses(self.rag_consumers, "chonkie_rag")
            },
            "thread_details": thread_statuses
        }
    
    def _run_consumer_thread(self, consumer, consumer_name: str) -> None:
        """Run a Chonkie consumer in a background thread."""
        try:
            self.logger.info(f"🎯 {consumer_name} Consumer thread started")
            self.logger.info(f"🔗 {consumer_name} subscribing to topics: {consumer.get_subscribed_topics()}")
            self.logger.info(f"👥 {consumer_name} consumer group: {consumer.group_id}")
            
            # Run blocking consume loop directly 
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
                
                # Simplified thread health check (single consumer type)
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
                    self.logger.error(f"❌ Chonkie consumer threads stopped unexpectedly: {dead_threads}")
                    self.logger.error("📊 Thread status details:")
                    for info in thread_details:
                        status = "🟢 ALIVE" if info["alive"] else "🔴 DEAD"
                        self.logger.error(f"   {status} {info['name']} (ID: {info['ident']}, Daemon: {info['daemon']})")
                    
                    # Log potential causes
                    self.logger.error("🔍 Potential causes:")
                    self.logger.error("   • Kafka connection issues")
                    self.logger.error("   • Chonkie dependency errors") 
                    self.logger.error("   • Weaviate connection problems")
                    self.logger.error("   • Resource constraints")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Chonkie RAG Orchestrator interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Main loop error: {e}")
            self.logger.exception("Full main loop exception details:")


def setup_signal_handlers(orchestrator: RAGOrchestrator) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, shutting down Chonkie RAG orchestrator...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function for standalone execution."""
    print("🎯 Chonkie RAG Processing Orchestrator")
    print("=" * 50)
    print("🚀 Starting unified high-performance RAG processing pipeline...")
    print("📄 Listens to: document-available events")
    print("⚡ Performance: 2-33x faster than legacy multi-stage pipeline")
    print("🔄 Pipeline: Unified Chonkie → Chunking+Embedding+Weaviate Storage")
    print("=" * 50)
    print("📖 Scaling examples:")
    print("   • Light load:    RAGOrchestrator(num_rag_consumers=1)")
    print("   • Balanced:      RAGOrchestrator(num_rag_consumers=2)")
    print("   • Heavy load:    RAGOrchestrator(num_rag_consumers=4)")
    print("=" * 50)
    print("Press Ctrl+C to stop")
    print()
    
    # Initialize orchestrator with example scaling configuration
    orchestrator = RAGOrchestrator(
        num_rag_consumers=2,    # Unified Chonkie consumers
        rag_group_id="chonkie_rag_production"
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
        print("✅ Chonkie RAG Service shutdown complete")


if __name__ == "__main__":
    main()