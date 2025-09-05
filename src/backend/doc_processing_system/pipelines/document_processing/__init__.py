# Document Processing Pipeline - Phase 1 Foundation

# Chonkie-based unified pipeline (Phase 1 migration)
from .chonkie_processor import ChonkieProcessor

# Backward compatibility aliases
DoclingProcessor = ChonkieProcessor  # Redirect to unified Chonkie processor

__all__ = ['ChonkieProcessor', 'DoclingProcessor']