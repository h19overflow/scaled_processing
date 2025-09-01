"""
Chunk Formatting Task - Stage 3 of RAG Processing Pipeline

Handles formatting of refined chunks into TextChunk models and file storage.
Part of the modular RAG processing pipeline.
"""

import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY


@task(
    name="chunk_formatting",
    description="Format final chunks into TextChunk models and save to file",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=60,  # Quick formatting task
    tags=["chunking", "formatting", "textchunk", "models"]
)
async def chunk_formatting_task(
    stage2_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Format refined chunks into TextChunk models and save to file.
    
    Args:
        stage2_result: Results from boundary refinement task
        
    Returns:
        Dict containing formatted TextChunk models and file path
        
    Raises:
        ValueError: If formatting fails
    """
    logger = get_run_logger()
    start_time = time.time()
    
    document_id = stage2_result["document_id"]
    final_chunks = stage2_result["final_chunks"]
    source_file_path = stage2_result.get("source_file_path", "unknown")
    
    logger.info(f"🔄 Starting chunk formatting task for {document_id}")
    logger.info(f"📄 Formatting {len(final_chunks)} chunks into TextChunk models")
    logger.info(f"📁 Source file: {source_file_path}")
    
    try:
        # Create TextChunk models
        text_chunks = []
        chunks_directory = Path("data/rag/chunks")
        chunks_directory.mkdir(parents=True, exist_ok=True)
        
        # Extract basic document information for metadata
        original_filename = Path(source_file_path).stem if source_file_path != "unknown" else document_id
        
        # Try to load page mapping from document metadata
        page_mapping, original_content = _load_document_metadata(source_file_path, document_id)
        total_content_length = len(original_content) if original_content else 0
        
        for i, chunk_content in enumerate(final_chunks):
            # Calculate approximate position of this chunk in original content
            chunk_start_pos = _estimate_chunk_position(chunk_content, original_content, i, len(final_chunks))
            
            # Get page number using real page mapping
            page_number = _extract_page_number(
                chunk_content, i, page_mapping, total_content_length, chunk_start_pos
            )
            # Generate deterministic chunk ID
            id_string = f"{document_id}_{i}"
            chunk_id = hashlib.md5(id_string.encode()).hexdigest()[:16]
            
            # Create TextChunk dictionary matching the model
            text_chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "content": chunk_content,
                "page_number": page_number,
                "chunk_index": i,
                "metadata": {
                    "chunk_length": len(chunk_content),
                    "word_count": len(chunk_content.split()),
                    "created_at": datetime.now().isoformat(),
                    "chunking_strategy": "two_stage_semantic",
                    "source_file_path": source_file_path,
                    "original_filename": original_filename,
                    "document_type": _get_document_type(original_filename),
                    "chunk_position": "start" if i == 0 else "end" if i == len(final_chunks) - 1 else "middle"
                }
            }
            
            text_chunks.append(text_chunk)
        
        # Save TextChunk models to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chunks_{document_id}_{timestamp}.json"
        chunks_path = chunks_directory / filename
        
        chunks_data = {
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
            "chunk_count": len(text_chunks),
            "chunks": text_chunks,  # List of TextChunk dictionaries
            "statistics": {
                "total_characters": sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks),
                "total_words": sum(chunk["metadata"]["word_count"] for chunk in text_chunks),
                "avg_chunk_length": round(sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks) / len(text_chunks), 1) if text_chunks else 0,
                "min_chunk_length": min(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0,
                "max_chunk_length": max(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0
            }
        }
        
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Chunk formatting complete: {len(text_chunks)} TextChunk models saved in {processing_time:.2f}s")
        logger.info(f"📄 Chunks saved to: {chunks_path}")
        
        # Return formatting results
        result = {
            "document_id": document_id,
            "chunk_count": len(text_chunks),
            "chunks_file_path": str(chunks_path),
            "text_chunks": text_chunks,
            "task_name": "chunk_formatting",
            "task_processing_time": round(processing_time, 3),
            "task_completed_at": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Chunk formatting task failed after {processing_time:.2f}s: {e}")
        raise


# HELPER FUNCTIONS
def _extract_page_number(chunk_content: str, chunk_index: int, page_mapping: dict = None, total_content_length: int = 0, chunk_start_pos: int = 0) -> int:
    """
    Extract page number using real page mapping from document processing.
    
    Args:
        chunk_content: The text content of the chunk
        chunk_index: The sequential index of the chunk
        page_mapping: Page mapping from document processing (optional)
        total_content_length: Total length of document content
        chunk_start_pos: Approximate start position of chunk in document
        
    Returns:
        int: Page number (1-based)
    """
    import re
    
    # First try to use real page mapping if available
    if page_mapping and total_content_length > 0:
        # Calculate approximate position of this chunk
        if chunk_start_pos == 0:
            # Estimate position based on chunk index
            chunk_start_pos = int((chunk_index / max(1, chunk_index + 1)) * total_content_length)
        
        # Find which page this position falls into
        for page_num, page_info in page_mapping.items():
            start_pos = page_info.get('start_pos', 0)
            end_pos = page_info.get('end_pos', total_content_length)
            
            if start_pos <= chunk_start_pos < end_pos:
                return int(page_num)
    
    # Fallback: Look for explicit page markers in content
    page_patterns = [
        r'Page\s*(\d+)',
        r'page\s*(\d+)',
        r'Page:\s*(\d+)',
        r'p\.?\s*(\d+)',
        r'pg\.?\s*(\d+)'
    ]
    
    for pattern in page_patterns:
        matches = re.findall(pattern, chunk_content)
        if matches:
            try:
                return int(matches[0])
            except (ValueError, IndexError):
                continue
    
    # Final fallback: Estimate based on chunk position
    # Assume average 2-3 chunks per page for most documents
    estimated_page = max(1, (chunk_index // 2) + 1)
    
    return estimated_page


def _load_document_metadata(source_file_path: str, document_id: str) -> tuple[dict, str]:
    """
    Load page mapping and original content from document processing metadata.
    
    Args:
        source_file_path: Path to the processed document file
        document_id: Document identifier
        
    Returns:
        tuple: (page_mapping_dict, original_content)
    """
    import json
    
    try:
        # Try to find document metadata file
        processed_path = Path(source_file_path).parent
        metadata_files = list(processed_path.glob("*metadata*.json"))
        
        if metadata_files:
            # Load the most recent metadata file
            metadata_file = max(metadata_files, key=lambda f: f.stat().st_mtime)
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            page_mapping = metadata.get("page_mapping", {})
            original_content = metadata.get("processed_content", "")
            
            return page_mapping, original_content
        
        # Fallback: try to read the processed document directly
        if Path(source_file_path).exists():
            with open(source_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            return {}, original_content
            
    except Exception as e:
        pass  # Silently handle errors
    
    return {}, ""


def _estimate_chunk_position(chunk_content: str, original_content: str, chunk_index: int, total_chunks: int) -> int:
    """
    Estimate the position of a chunk within the original document content.
    
    Args:
        chunk_content: Content of the current chunk
        original_content: Full original document content
        chunk_index: Index of the current chunk
        total_chunks: Total number of chunks
        
    Returns:
        int: Estimated start position of chunk in original content
    """
    if not original_content or not chunk_content:
        # Fallback to proportional estimate
        return int((chunk_index / max(1, total_chunks)) * len(original_content or ""))
    
    try:
        # Try to find the chunk content in the original content
        # Use first few words to find approximate position
        chunk_words = chunk_content.strip().split()[:10]  # First 10 words
        if chunk_words:
            search_phrase = " ".join(chunk_words)
            position = original_content.find(search_phrase)
            
            if position != -1:
                return position
    
    except Exception:
        pass
    
    # Fallback to proportional estimate
    return int((chunk_index / max(1, total_chunks)) * len(original_content))


def _get_document_type(filename: str) -> str:
    """
    Determine document type from filename extension.
    
    Args:
        filename: The original filename
        
    Returns:
        str: Document type classification
    """
    if not filename or filename == "unknown":
        return "unknown"
    
    filename_lower = filename.lower()
    
    if filename_lower.endswith(('.pdf', '.PDF')):
        return "pdf"
    elif filename_lower.endswith(('.doc', '.docx', '.DOC', '.DOCX')):
        return "word"
    elif filename_lower.endswith(('.txt', '.TXT')):
        return "text"
    elif filename_lower.endswith(('.md', '.markdown', '.MD')):
        return "markdown"
    elif filename_lower.endswith(('.html', '.htm', '.HTML', '.HTM')):
        return "html"
    elif filename_lower.endswith(('.ppt', '.pptx', '.PPT', '.PPTX')):
        return "powerpoint"
    elif filename_lower.endswith(('.xls', '.xlsx', '.XLS', '.XLSX')):
        return "excel"
    else:
        return "other"