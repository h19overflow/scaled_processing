"""
Interface definitions for the document processing system.
"""

from .agents import *
from .messaging import *
from .orchestration import *
from .persistence import *
from .evaluation import *

__all__ = [
    # Agent interfaces
    "BaseAgent",
    "IFieldDiscoveryAgent", 
    "IExtractionAgent",
    "IOrchestratorAgent",
    "IImageAgent",
    
    # Parser interfaces
    "IDocumentParser",
    "IChunker",
    
    # Model interfaces
    "IDocument",
    "IChunk",
    
    # Messaging interfaces
    "IEventPublisher",
    "IEventConsumer",
    
    # Persistence interfaces
    "IPersistenceRepository",
    
    # Orchestration interfaces
    "IWorkflowOrchestrator",
    "IAPIController",
    
    # Evaluation interfaces
    "IQueryEngine",
    "IEvaluator",
]