"""Vision processor - orchestrates the complete vision pipeline."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from PIL import Image

from .vision_config import VisionConfig
from .image_classifier import ImageClassifier
from .vision_agent import VisionAgent
from .markdown_enhancer import MarkdownEnhancer


class VisionProcessor:
    """Orchestrates smart vision processing pipeline."""
    
    def __init__(self, config: VisionConfig = None):
        """Initialize vision processor with all components."""
        self.config = config or VisionConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.classifier = ImageClassifier(self.config)
        self.vision_agent = VisionAgent(self.config)
        self.enhancer = MarkdownEnhancer()
        
        # Concurrency controls
        self.classification_semaphore = asyncio.Semaphore(self.config.classification_concurrency)
        self.analysis_semaphore = asyncio.Semaphore(self.config.analysis_concurrency)
        
        # Metrics
        self.metrics = {
            'total_images': 0,
            'classified_skip': 0,
            'classified_analyze': 0,
            'analysis_completed': 0,
            'classification_tokens': 0,
            'analysis_tokens': 0
        }
        
        self.logger.info("VisionProcessor initialized")
    
    async def process_document_images(self, extracted_images: Dict[str, str], 
                                    content: str, context: str = "") -> str:
        """Process all images in a document and enhance content.
        
        Args:
            extracted_images: Dict of {image_id: image_path}
            content: Original markdown content
            context: Document context for better analysis
            
        Returns:
            Enhanced markdown content
        """
        if not self.config.enable_vision_processing or not extracted_images:
            return content
        
        self.logger.info(f"Processing {len(extracted_images)} images with vision AI")
        
        # Reset metrics
        self.metrics['total_images'] = len(extracted_images)
        
        # Load images
        images = []
        for img_id, img_path in extracted_images.items():
            try:
                img_obj = Image.open(img_path)
                images.append((img_id, img_path, img_obj))
            except Exception as e:
                self.logger.warning(f"Failed to load image {img_path}: {e}")
        
        # Phase 1: Classify images (if enabled)
        if self.config.enable_classification_filter:
            descriptions = await self._process_with_classification(images, context)
        else:
            descriptions = await self._process_all_images(images, context)
        
        # Phase 2: Enhance markdown content
        enhanced_content = self.enhancer.enhance_content(content, descriptions)
        
        # Log metrics
        self._log_metrics()
        
        return enhanced_content
    
    async def _process_with_classification(self, images: List[Tuple], context: str) -> Dict[str, Dict]:
        """Process images with smart classification filtering."""
        
        # Step 1: Classify all images
        classification_tasks = [
            self._classify_with_semaphore(img_id, img_obj, context)
            for img_id, img_path, img_obj in images
        ]
        
        classifications = await asyncio.gather(*classification_tasks, return_exceptions=True)
        
        # Step 2: Filter images for analysis
        images_to_analyze = []
        for i, (img_id, img_path, img_obj) in enumerate(images):
            classification = classifications[i]
            
            if isinstance(classification, dict) and classification.get('action') == 'analyze':
                images_to_analyze.append((img_id, img_path, img_obj, classification))
            elif isinstance(classification, dict):
                self.metrics['classified_skip'] += 1
        
        self.metrics['classified_analyze'] = len(images_to_analyze)
        
        # Step 3: Analyze filtered images
        if not images_to_analyze:
            return {}
        
        analysis_tasks = [
            self._analyze_with_semaphore(img_id, img_obj, context, classification)
            for img_id, img_path, img_obj, classification in images_to_analyze
        ]
        
        analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Step 4: Compile results
        descriptions = {}
        for i, (img_id, img_path, img_obj, classification) in enumerate(images_to_analyze):
            if isinstance(analyses[i], str) and "Failed" not in analyses[i]:
                descriptions[img_id] = {
                    'description': analyses[i],
                    'classification': classification,
                    'image_path': img_path
                }
                self.metrics['analysis_completed'] += 1
        
        return descriptions
    
    async def _process_all_images(self, images: List[Tuple], context: str) -> Dict[str, Dict]:
        """Process all images without classification filtering."""
        
        analysis_tasks = [
            self._analyze_with_semaphore(img_id, img_obj, context, {'action': 'analyze', 'confidence': 1.0})
            for img_id, img_path, img_obj in images
        ]
        
        analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        descriptions = {}
        for i, (img_id, img_path, img_obj) in enumerate(images):
            if isinstance(analyses[i], str) and "Failed" not in analyses[i]:
                descriptions[img_id] = {
                    'description': analyses[i],
                    'classification': {'action': 'analyze', 'confidence': 1.0},
                    'image_path': img_path
                }
                self.metrics['analysis_completed'] += 1
        
        return descriptions
    
    async def _classify_with_semaphore(self, img_id: str, img_obj: Image.Image, context: str) -> Dict:
        """Classify image with concurrency control."""
        async with self.classification_semaphore:
            result = await self.classifier.classify_image(img_obj, context)
            self.metrics['classification_tokens'] += result.get('tokens_used', 0)
            return result
    
    async def _analyze_with_semaphore(self, img_id: str, img_obj: Image.Image, 
                                    context: str, classification: Dict) -> str:
        """Analyze image with concurrency control."""
        async with self.analysis_semaphore:
            description = await self.vision_agent.describe_image_async(img_obj, context)
            # Rough token estimation
            estimated_tokens = len(description.split()) * 1.3
            self.metrics['analysis_tokens'] += estimated_tokens
            return description
    
    def _log_metrics(self):
        """Log processing metrics."""
        total = self.metrics['total_images']
        analyzed = self.metrics['analysis_completed']
        skipped = self.metrics['classified_skip']
        
        if total > 0:
            self.logger.info(f"""Vision Processing Summary:
├── Total Images: {total}
├── Analyzed: {analyzed} ({analyzed/total*100:.1f}%)
├── Skipped: {skipped} ({skipped/total*100:.1f}%)
├── Classification Tokens: {self.metrics['classification_tokens']}
└── Analysis Tokens: {int(self.metrics['analysis_tokens'])}""")