"""
Document chunking node.
"""

from typing import List, Dict, Any

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from ..models.state import MultiAgentState
from ..models.document import DocumentChunk
from ..config.settings import Settings


def chunk_document(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Chunk document into processing batches."""
    try:
        chunks = _create_chunks(
            text=state["document_text"],
            document_id=state["document_id"],
            config=settings.chunking
        )

        return {
            **state,
            "chunks": chunks,
            "status": "chunked"
        }

    except Exception as e:
        return {
            **state,
            "error": f"Document chunking failed: {str(e)}",
            "status": "error"
        }


def _create_chunks(text: str, document_id: str, config) -> List[DocumentChunk]:
    """Create document chunks based on configuration."""
    max_tokens = config.max_tokens
    overlap_tokens = config.overlap_tokens

    if config.use_tiktoken and TIKTOKEN_AVAILABLE:
        return _tiktoken_chunk(text, max_tokens, overlap_tokens)
    else:
        return _simple_chunk(text, max_tokens, overlap_tokens)


def _tiktoken_chunk(text: str, max_tokens: int, overlap_tokens: int) -> List[DocumentChunk]:
    """Chunk using tiktoken tokenizer."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= max_tokens:
            return [DocumentChunk(
                chunk_id=0,
                text=text,
                start_char=0,
                end_char=len(text),
                token_count=total_tokens
            )]

        chunks = []
        chunk_id = 0
        start_token = 0

        while start_token < total_tokens:
            end_token = min(start_token + max_tokens, total_tokens)
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = encoding.decode(chunk_tokens)

            start_char = _token_to_char_position(text, tokens, start_token, encoding)
            end_char = _token_to_char_position(text, tokens, end_token, encoding)

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                token_count=len(chunk_tokens)
            )
            chunks.append(chunk)

            if end_token < total_tokens:
                start_token = end_token - overlap_tokens
            else:
                break

            chunk_id += 1

        return chunks

    except Exception:
        return _simple_chunk(text, max_tokens, overlap_tokens)


def _simple_chunk(text: str, max_tokens: int, overlap_tokens: int) -> List[DocumentChunk]:
    """Simple character-based chunking fallback."""
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    total_chars = len(text)

    if total_chars <= max_chars:
        return [DocumentChunk(
            chunk_id=0,
            text=text,
            start_char=0,
            end_char=total_chars,
            token_count=total_chars // 4
        )]

    chunks = []
    chunk_id = 0
    start_char = 0

    while start_char < total_chars:
        end_char = min(start_char + max_chars, total_chars)

        # Try to break at word boundaries
        if end_char < total_chars:
            for i in range(min(100, end_char - start_char)):
                if text[end_char - i - 1] == ' ':
                    end_char = end_char - i
                    break

        chunk_text = text[start_char:end_char]
        estimated_tokens = len(chunk_text) // 4

        chunk = DocumentChunk(
            chunk_id=chunk_id,
            text=chunk_text,
            start_char=start_char,
            end_char=end_char,
            token_count=estimated_tokens
        )
        chunks.append(chunk)

        if end_char >= total_chars:
            break

        start_char = max(start_char + 1, end_char - overlap_chars)
        chunk_id += 1

    return chunks


def _token_to_char_position(text: str, tokens: List[int], token_index: int, encoding) -> int:
    """Convert token index to character position in original text."""
    if token_index == 0:
        return 0
    if token_index >= len(tokens):
        return len(text)

    partial_tokens = tokens[:token_index]
    partial_text = encoding.decode(partial_tokens)
    return len(partial_text)
