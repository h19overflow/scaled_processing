"""
Isolated ChromaDB Worker - Subprocess-based ChromaDB operations to avoid segmentation faults

This module provides a safe way to perform ChromaDB operations in a separate process
to avoid segmentation faults that occur in multi-threaded environments on Windows.
"""

import json
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configure multiprocessing to use spawn method on Windows for better isolation
if sys.platform.startswith('win'):
    multiprocessing.set_start_method('spawn', force=True)


def chromadb_worker_process(
    embeddings_file_path: str,
    collection_name: str,
    result_queue: multiprocessing.Queue,
    log_level: str = "INFO"
):
    """
    Isolated ChromaDB worker process for safe vector storage operations.
    
    This function runs in a completely separate process to avoid segmentation faults
    that occur when ChromaDB operations run in multi-threaded environments.
    
    Args:
        embeddings_file_path: Path to embeddings JSON file
        collection_name: ChromaDB collection name
        result_queue: Queue to return results to parent process
        log_level: Logging level for the worker process
    """
    # Set up logging for the worker process
    logging.basicConfig(level=getattr(logging, log_level), format='%(asctime)s - %(levelname)s - [ChromaDBWorker] %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔧 ChromaDB worker process started (PID: {os.getpid()})")
        logger.info(f"💾 Processing file: {embeddings_file_path}")
        logger.info(f"🗄️ Target collection: {collection_name}")
        
        # Import ChromaDB dependencies only in the isolated process
        sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
        from src.backend.doc_processing_system.core_deps.chromadb.chunk_ingestion_engine import ChunkIngestionEngine
        
        # Create a fresh ChunkIngestionEngine instance in this isolated process
        logger.info("🏗️ Creating isolated ChunkIngestionEngine instance...")
        ingestion_engine = ChunkIngestionEngine()
        
        if not ingestion_engine:
            raise Exception("Failed to create ChunkIngestionEngine in worker process")
        
        logger.info("✅ ChunkIngestionEngine created successfully in worker process")
        
        # Perform the ChromaDB ingestion operation
        logger.info("🚀 Starting isolated ChromaDB ingestion...")
        start_time = time.time()
        
        success = ingestion_engine.ingest_from_chromadb_ready_file(
            embeddings_file_path=embeddings_file_path,
            collection_name=collection_name
        )
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ ChromaDB operation completed in {processing_time:.2f}s")
        
        if success:
            logger.info("✅ ChromaDB ingestion completed successfully in worker process")
            
            # Get ingestion stats
            try:
                stats = ingestion_engine.get_ingestion_stats(collection_name)
                logger.info(f"📊 Ingestion stats: {stats}")
            except Exception as stats_error:
                logger.warning(f"⚠️ Could not get stats: {stats_error}")
                stats = {}
            
            result = {
                "success": True,
                "processing_time": processing_time,
                "stats": stats,
                "worker_pid": os.getpid()
            }
        else:
            logger.error("❌ ChromaDB ingestion failed in worker process")
            result = {
                "success": False,
                "processing_time": processing_time,
                "error": "ChromaDB ingestion failed",
                "worker_pid": os.getpid()
            }
        
        # Send result back to parent process
        result_queue.put(result)
        logger.info(f"📤 Result sent back to parent process: success={result['success']}")
        
    except Exception as e:
        logger.error(f"❌ ChromaDB worker process error: {e}")
        import traceback
        logger.error(f"📋 Worker process traceback: {traceback.format_exc()}")
        
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "worker_pid": os.getpid()
        }
        
        try:
            result_queue.put(error_result)
        except Exception as queue_error:
            logger.error(f"❌ Failed to send error result to queue: {queue_error}")
        
    finally:
        logger.info(f"🔚 ChromaDB worker process finished (PID: {os.getpid()})")


class IsolatedChromaDBWorker:
    """
    Manager for isolated ChromaDB operations using subprocess to prevent segmentation faults.
    
    This class provides a safe interface for ChromaDB operations by running them in a
    separate process, avoiding the multi-threading issues that cause segmentation faults.
    """
    
    def __init__(self, timeout: int = 180):
        """
        Initialize the isolated ChromaDB worker manager.
        
        Args:
            timeout: Maximum time to wait for ChromaDB operations (seconds)
        """
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Ensure we're using spawn method for better isolation
        if sys.platform.startswith('win'):
            try:
                multiprocessing.set_start_method('spawn', force=True)
                self.logger.info("✅ Using 'spawn' multiprocessing method for Windows isolation")
            except RuntimeError:
                # Already set, which is fine
                self.logger.debug("🔍 Multiprocessing method already set")
    
    def ingest_from_chromadb_ready_file(
        self,
        embeddings_file_path: str,
        collection_name: str = "rag_documents"
    ) -> Dict[str, Any]:
        """
        Safely ingest embeddings using isolated ChromaDB worker process.
        
        Args:
            embeddings_file_path: Path to embeddings JSON file
            collection_name: ChromaDB collection name
            
        Returns:
            Dict containing ingestion results
        """
        self.logger.info("🛡️ Starting isolated ChromaDB ingestion...")
        self.logger.info(f"💾 File: {embeddings_file_path}")
        self.logger.info(f"🗄️ Collection: {collection_name}")
        self.logger.info(f"⏰ Timeout: {self.timeout}s")
        
        # Create queue for communication with worker process
        result_queue = multiprocessing.Queue()
        
        try:
            # Start the isolated worker process
            self.logger.info("🚀 Starting isolated ChromaDB worker process...")
            worker_process = multiprocessing.Process(
                target=chromadb_worker_process,
                args=(embeddings_file_path, collection_name, result_queue, "INFO"),
                name="ChromaDBWorker"
            )
            
            start_time = time.time()
            worker_process.start()
            
            self.logger.info(f"✅ Worker process started with PID: {worker_process.pid}")
            
            # Wait for the worker process to complete with timeout
            worker_process.join(timeout=self.timeout)
            
            processing_time = time.time() - start_time
            
            if worker_process.is_alive():
                # Process timed out
                self.logger.error(f"⏰ ChromaDB worker process timed out after {self.timeout}s")
                worker_process.terminate()
                worker_process.join(timeout=10)  # Give it time to terminate gracefully
                
                if worker_process.is_alive():
                    self.logger.error("💀 Force killing hanging ChromaDB worker process")
                    worker_process.kill()
                    worker_process.join()
                
                return {
                    "success": False,
                    "error": f"ChromaDB operation timed out after {self.timeout}s",
                    "timeout": True,
                    "processing_time": processing_time
                }
            
            # Check worker process exit code
            if worker_process.exitcode == 0:
                # Process completed successfully, get result
                try:
                    if not result_queue.empty():
                        result = result_queue.get_nowait()
                        result["processing_time"] = processing_time
                        
                        if result.get("success"):
                            self.logger.info(f"✅ Isolated ChromaDB ingestion completed successfully in {processing_time:.2f}s")
                            self.logger.info(f"👨‍💻 Worker PID: {result.get('worker_pid')}")
                        else:
                            self.logger.error(f"❌ ChromaDB ingestion failed in worker process")
                            
                        return result
                    else:
                        self.logger.error("❌ No result received from worker process")
                        return {
                            "success": False,
                            "error": "No result received from worker process",
                            "processing_time": processing_time
                        }
                        
                except Exception as queue_error:
                    self.logger.error(f"❌ Error getting result from queue: {queue_error}")
                    return {
                        "success": False,
                        "error": f"Error getting result from worker: {queue_error}",
                        "processing_time": processing_time
                    }
            else:
                # Process failed
                exit_code = worker_process.exitcode
                self.logger.error(f"❌ ChromaDB worker process failed with exit code: {exit_code}")
                
                # Windows specific error code handling
                if exit_code == 3221225477:  # 0xc0000005 - ACCESS_VIOLATION (segmentation fault)
                    self.logger.error("💀 ChromaDB worker process crashed with ACCESS_VIOLATION (segmentation fault)")
                    self.logger.error("🔧 This is the known ChromaDB Windows DLL compatibility issue")
                    self.logger.error("🛡️ However, the isolated worker prevented the main process from crashing")
                    return {
                        "success": False,
                        "error": "ChromaDB segmentation fault caught by isolated worker",
                        "segmentation_fault": True,
                        "exit_code": exit_code,
                        "processing_time": processing_time,
                        "graceful_recovery": True
                    }
                elif exit_code < 0:
                    self.logger.error(f"💀 ChromaDB worker process terminated by signal: {-exit_code}")
                
                # Try to get error details from queue
                error_details = "Unknown worker process error"
                try:
                    if not result_queue.empty():
                        error_result = result_queue.get_nowait()
                        error_details = error_result.get("error", error_details)
                except:
                    pass
                
                return {
                    "success": False,
                    "error": error_details,
                    "exit_code": worker_process.exitcode,
                    "processing_time": processing_time
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error managing ChromaDB worker process: {e}")
            import traceback
            self.logger.error(f"📋 Manager traceback: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "manager_error": True
            }
        
        finally:
            # Clean up
            try:
                result_queue.close()
                result_queue.join_thread()
            except Exception as cleanup_error:
                self.logger.warning(f"⚠️ Queue cleanup error: {cleanup_error}")


# Global instance for easy import
isolated_chromadb_worker = IsolatedChromaDBWorker(timeout=360000)


def get_isolated_chromadb_worker() -> IsolatedChromaDBWorker:
    """Get the global isolated ChromaDB worker instance."""
    return isolated_chromadb_worker