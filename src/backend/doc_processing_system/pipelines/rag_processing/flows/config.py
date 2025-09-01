"""
RAG Processing Flow Configuration

Centralized configuration for the RAG processing pipeline Prefect flow.
Defines timeouts, retries, and model parameters for consistent execution.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TaskTimeouts:
    """Timeout configuration for pipeline tasks."""
    chunking: int = 300      # 5 minutes
    embeddings: int = 600    # 10 minutes  
    storage: int = 120       # 2 minutes
    pipeline: int = 1800     # 30 minutes total


@dataclass
class RetryConfig:
    """Retry configuration for pipeline tasks."""
    max_retries: int = 3
    retry_delay_seconds: int = 30
    flow_retries: int = 1
    flow_retry_delay_seconds: int = 60


@dataclass
class ChunkingConfig:
    """Two-stage chunking configuration."""
    chunk_size: int = 700
    semantic_threshold: float = 0.75
    boundary_context: int = 200
    concurrent_agents: int = 10
    model_name: str = "gemini-2.0-flash"


@dataclass
class EmbeddingConfig:
    """Embeddings generation configuration."""
    model_name: str = "BAAI/bge-large-en-v1.5"
    batch_size: int = 32
    fallback_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class StorageConfig:
    """Vector storage configuration."""
    collection_name: str = "rag_documents"
    persist_directory: str = "data/chroma"
    distance_metric: str = "cosine"


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    timeouts: TaskTimeouts
    retries: RetryConfig
    chunking: ChunkingConfig
    embeddings: EmbeddingConfig
    storage: StorageConfig
    
    @classmethod
    def default(cls) -> 'PipelineConfig':
        """Create default pipeline configuration."""
        return cls(
            timeouts=TaskTimeouts(),
            retries=RetryConfig(),
            chunking=ChunkingConfig(),
            embeddings=EmbeddingConfig(),
            storage=StorageConfig()
        )
    
    @classmethod
    def fast_testing(cls) -> 'PipelineConfig':
        """Create configuration optimized for fast testing."""
        return cls(
            timeouts=TaskTimeouts(
                chunking=120,     # 2 minutes
                embeddings=300,   # 5 minutes
                storage=60,       # 1 minute
                pipeline=600      # 10 minutes
            ),
            retries=RetryConfig(
                max_retries=2,
                retry_delay_seconds=10,
                flow_retries=1,
                flow_retry_delay_seconds=30
            ),
            chunking=ChunkingConfig(
                chunk_size=300,
                semantic_threshold=0.7,
                concurrent_agents=3,
                model_name="gemini-2.0-flash"
            ),
            embeddings=EmbeddingConfig(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                batch_size=16
            ),
            storage=StorageConfig()
        )
    
    @classmethod
    def production(cls) -> 'PipelineConfig':
        """Create configuration optimized for production."""
        return cls(
            timeouts=TaskTimeouts(
                chunking=600,     # 10 minutes
                embeddings=1200,  # 20 minutes
                storage=300,      # 5 minutes
                pipeline=3600     # 1 hour
            ),
            retries=RetryConfig(
                max_retries=5,
                retry_delay_seconds=60,
                flow_retries=2,
                flow_retry_delay_seconds=120
            ),
            chunking=ChunkingConfig(
                chunk_size=700,
                semantic_threshold=0.75,
                concurrent_agents=15,
                model_name="gemini-2.0-flash"
            ),
            embeddings=EmbeddingConfig(
                model_name="jinaai/jina-embeddings-v3",
                batch_size=64
            ),
            storage=StorageConfig()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "timeouts": {
                "chunking": self.timeouts.chunking,
                "embeddings": self.timeouts.embeddings,
                "storage": self.timeouts.storage,
                "pipeline": self.timeouts.pipeline
            },
            "retries": {
                "max_retries": self.retries.max_retries,
                "retry_delay_seconds": self.retries.retry_delay_seconds,
                "flow_retries": self.retries.flow_retries,
                "flow_retry_delay_seconds": self.retries.flow_retry_delay_seconds
            },
            "chunking": {
                "chunk_size": self.chunking.chunk_size,
                "semantic_threshold": self.chunking.semantic_threshold,
                "boundary_context": self.chunking.boundary_context,
                "concurrent_agents": self.chunking.concurrent_agents,
                "model_name": self.chunking.model_name
            },
            "embeddings": {
                "model_name": self.embeddings.model_name,
                "batch_size": self.embeddings.batch_size,
                "fallback_model": self.embeddings.fallback_model
            },
            "storage": {
                "collection_name": self.storage.collection_name,
                "persist_directory": self.storage.persist_directory,
                "distance_metric": self.storage.distance_metric
            }
        }


# Predefined configurations
DEFAULT_CONFIG = PipelineConfig.default()
TESTING_CONFIG = PipelineConfig.fast_testing()
PRODUCTION_CONFIG = PipelineConfig.production()


# Configuration selection utility
def get_config(mode: str = "default") -> PipelineConfig:
    """Get pipeline configuration by mode.
    
    Args:
        mode: Configuration mode ("default", "testing", "production")
        
    Returns:
        PipelineConfig instance
        
    Raises:
        ValueError: If mode is not recognized
    """
    config_map = {
        "default": DEFAULT_CONFIG,
        "testing": TESTING_CONFIG,
        "production": PRODUCTION_CONFIG
    }
    
    if mode not in config_map:
        raise ValueError(f"Unknown config mode: {mode}. Available: {list(config_map.keys())}")
    
    return config_map[mode]