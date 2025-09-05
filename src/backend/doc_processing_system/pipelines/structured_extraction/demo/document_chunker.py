"""
Document chunker for multi-agent schema discovery.
Splits documents into token-based batches for sequential processing.
"""

from typing import List, Dict, Any
from dataclasses import dataclass

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

@dataclass
class DocumentChunk:
    """A chunk of document with metadata."""
    chunk_id: int
    text: str
    start_char: int
    end_char: int
    token_count: int

class DocumentChunker:
    """Chunks documents into manageable pieces for multi-agent processing."""
    
    def __init__(self, max_tokens: int = 1500, overlap_tokens: int = 200):
        """Initialize document chunker."""
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.max_chars = max_tokens * 4  # Rough char-to-token ratio
        self.overlap_chars = overlap_tokens * 4
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
                self.use_tiktoken = True
            except Exception:
                self.use_tiktoken = False
        else:
            self.use_tiktoken = False
    
    def chunk_document(self, text: str, document_id: str) -> List[DocumentChunk]:
        """Split document into overlapping chunks."""
        if self.use_tiktoken:
            return self._tiktoken_chunk(text)
        else:
            return self._simple_chunk(text)
    
    def _tiktoken_chunk(self, text: str) -> List[DocumentChunk]:
        """Chunk using tiktoken tokenizer."""
        try:
            tokens = self.encoding.encode(text)
            total_tokens = len(tokens)
            
            if total_tokens <= self.max_tokens:
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
                end_token = min(start_token + self.max_tokens, total_tokens)
                chunk_tokens = tokens[start_token:end_token]
                chunk_text = self.encoding.decode(chunk_tokens)
                
                start_char = self._token_to_char_position(text, tokens, start_token)
                end_char = self._token_to_char_position(text, tokens, end_token)
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    start_char=start_char,
                    end_char=end_char,
                    token_count=len(chunk_tokens)
                )
                chunks.append(chunk)
                
                if end_token < total_tokens:
                    start_token = end_token - self.overlap_tokens
                else:
                    break
                
                chunk_id += 1
            
            return chunks
            
        except Exception:
            # Fallback to simple chunking
            return self._simple_chunk(text)
    
    def _simple_chunk(self, text: str) -> List[DocumentChunk]:
        """Simple character-based chunking fallback."""
        total_chars = len(text)
        
        if total_chars <= self.max_chars:
            return [DocumentChunk(
                chunk_id=0,
                text=text,
                start_char=0,
                end_char=total_chars,
                token_count=total_chars // 4  # Rough estimate
            )]
        
        chunks = []
        chunk_id = 0
        start_char = 0
        
        while start_char < total_chars:
            end_char = min(start_char + self.max_chars, total_chars)
            
            # Try to break at word boundaries
            if end_char < total_chars:
                # Look for last space within 100 chars of target end
                for i in range(min(100, end_char - start_char)):
                    if text[end_char - i - 1] == ' ':
                        end_char = end_char - i
                        break
            
            chunk_text = text[start_char:end_char]
            estimated_tokens = len(chunk_text) // 4  # Rough estimate
            
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
                
            start_char = max(start_char + 1, end_char - self.overlap_chars)
            chunk_id += 1
        
        return chunks
    
    def get_chunk_summary(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """Get summary statistics for chunks."""
        total_chars = sum(chunk.end_char - chunk.start_char for chunk in chunks)
        total_tokens = sum(chunk.token_count for chunk in chunks)
        
        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "total_tokens": total_tokens,
            "avg_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0,
            "chunks_info": [
                {
                    "chunk_id": chunk.chunk_id,
                    "tokens": chunk.token_count,
                    "chars": chunk.end_char - chunk.start_char,
                    "char_range": f"{chunk.start_char}-{chunk.end_char}"
                }
                for chunk in chunks
            ]
        }
    
    # HELPER FUNCTIONS
    
    def _token_to_char_position(self, text: str, tokens: List[int], token_index: int) -> int:
        """Convert token index to character position in original text."""
        if token_index == 0:
            return 0
        if token_index >= len(tokens):
            return len(text)
        
        # Decode up to token_index to find character position
        partial_tokens = tokens[:token_index]
        partial_text = self.encoding.decode(partial_tokens)
        return len(partial_text)