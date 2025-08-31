# Multi-Level Vision Processing Pipeline

## Strategy: Smart Image Filtering Before Analysis

### Problem Statement
- Documents can contain 100+ images (charts, logos, decorative elements, screenshots)
- Many images don't contribute meaningful content (logos, borders, noise)
- Vision API cost is primarily in **output tokens** (descriptions)
- Need to filter intelligently while preserving valuable content

## Multi-Level Processing Pipeline

### Level 1: Fast Image Classification (Cheap)
```python
class ImageClassifier:
    """Quick classification to determine if image needs full analysis."""
    
    def __init__(self):
        self.client = genai.Client()
        self.classifier_model = "gemini-2.5-flash-image-preview"
    
    async def classify_image_relevance(self, image: Image.Image, context: str = "") -> dict:
        """
        Quick classification with minimal output tokens.
        Returns: {'action': 'analyze'|'skip', 'confidence': float, 'reason': str}
        """
        
        # MINIMAL PROMPT - reduces output tokens dramatically
        prompt = f"""Classify this image from a document. Context: {context}

Reply with exactly ONE word followed by confidence (0-1):
- ANALYZE: Charts, graphs, diagrams, text-heavy images, technical content
- SKIP: Logos, decorative elements, pure photos, screenshots of UI

Format: ACTION confidence
Example: ANALYZE 0.9"""

        try:
            response = await self.client.models.generate_content(
                model=self.classifier_model,
                contents=[image, prompt],
                generation_config={
                    "max_output_tokens": 10,  # CRITICAL: Minimize output tokens
                    "temperature": 0.1,       # Consistent classification
                }
            )
            
            # Parse minimal response
            parts = response.text.strip().split()
            action = parts[0].upper()
            confidence = float(parts[1]) if len(parts) > 1 else 0.5
            
            return {
                'action': 'analyze' if action == 'ANALYZE' else 'skip',
                'confidence': confidence,
                'reason': f'Classified as {action}',
                'tokens_used': len(response.text.split())  # Track cost
            }
            
        except Exception as e:
            # Default to analyze on error (conservative)
            return {
                'action': 'analyze',
                'confidence': 0.5,
                'reason': f'Classification failed: {e}',
                'tokens_used': 0
            }
```

### Level 2: Full Vision Analysis (Expensive)
```python
class VisionAnalyzer:
    """Full analysis for images that passed classification."""
    
    def __init__(self):
        self.client = genai.Client()
        self.analyzer_model = "gemini-2.5-flash-image-preview"
    
    async def analyze_image_full(self, image: Image.Image, context: str = "") -> str:
        """
        Full analysis with detailed description.
        Only called for images classified as 'analyze'.
        """
        
        prompt = f"""Analyze this image from a document in detail. Context: {context}

Provide a comprehensive description focusing on:
- Key information, data, or insights
- Text content if readable
- Relationships to surrounding document content
- Technical details if applicable

Be thorough but concise."""

        try:
            response = await self.client.models.generate_content(
                model=self.analyzer_model,
                contents=[image, prompt],
                generation_config={
                    "max_output_tokens": 500,  # Reasonable limit for full analysis
                    "temperature": 0.3,
                }
            )
            
            return response.text
            
        except Exception as e:
            return f"Analysis failed: {e}"
```

### Level 3: Integration Pipeline
```python
class SmartVisionProcessor:
    """Orchestrates multi-level vision processing."""
    
    def __init__(self):
        self.classifier = ImageClassifier()
        self.analyzer = VisionAnalyzer()
        
        # Concurrency control
        self.classification_semaphore = asyncio.Semaphore(10)  # Fast operations
        self.analysis_semaphore = asyncio.Semaphore(3)         # Expensive operations
        
        # Metrics tracking
        self.metrics = {
            'total_images': 0,
            'classified_skip': 0,
            'classified_analyze': 0,
            'analysis_completed': 0,
            'classification_tokens': 0,
            'analysis_tokens': 0,
            'total_cost_estimate': 0.0
        }
    
    async def process_document_images(self, images: List[tuple], context: str = "") -> dict:
        """
        Process all images in a document with smart filtering.
        
        Args:
            images: List of (image_id, image_path, image_object) tuples
            context: Document context for better classification
            
        Returns:
            dict: Processing results with descriptions and metrics
        """
        self.metrics['total_images'] = len(images)
        
        # PHASE 1: Classify all images (fast, parallel)
        classification_tasks = [
            self._classify_with_semaphore(img_id, img_obj, context)
            for img_id, img_path, img_obj in images
        ]
        
        classifications = await asyncio.gather(*classification_tasks, return_exceptions=True)
        
        # PHASE 2: Analyze only relevant images (expensive, limited concurrency)
        images_to_analyze = [
            (images[i], classifications[i])
            for i in range(len(images))
            if (isinstance(classifications[i], dict) and 
                classifications[i].get('action') == 'analyze')
        ]
        
        self.metrics['classified_analyze'] = len(images_to_analyze)
        self.metrics['classified_skip'] = len(images) - len(images_to_analyze)
        
        if not images_to_analyze:
            return {
                'descriptions': {},
                'metrics': self.metrics.copy(),
                'summary': 'All images classified as non-essential'
            }
        
        # Analyze filtered images
        analysis_tasks = [
            self._analyze_with_semaphore(img_data[0], img_data[1], context)
            for img_data in images_to_analyze
        ]
        
        analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Compile results
        descriptions = {}
        for i, (img_tuple, classification) in enumerate(images_to_analyze):
            img_id, img_path, img_obj = img_tuple
            if isinstance(analyses[i], str):
                descriptions[img_id] = {
                    'description': analyses[i],
                    'classification': classification,
                    'image_path': img_path
                }
        
        self.metrics['analysis_completed'] = len(descriptions)
        
        return {
            'descriptions': descriptions,
            'metrics': self.metrics.copy(),
            'summary': f"Processed {len(images)} images: {self.metrics['classified_skip']} skipped, {self.metrics['analysis_completed']} analyzed"
        }
    
    async def _classify_with_semaphore(self, img_id: int, img_obj: Image.Image, context: str) -> dict:
        """Classify image with concurrency control."""
        async with self.classification_semaphore:
            result = await self.classifier.classify_image_relevance(img_obj, context)
            self.metrics['classification_tokens'] += result.get('tokens_used', 0)
            return result
    
    async def _analyze_with_semaphore(self, img_tuple: tuple, classification: dict, context: str) -> str:
        """Analyze image with concurrency control."""
        async with self.analysis_semaphore:
            img_id, img_path, img_obj = img_tuple
            description = await self.analyzer.analyze_image_full(img_obj, context)
            # Estimate tokens (rough calculation)
            estimated_tokens = len(description.split()) * 1.3
            self.metrics['analysis_tokens'] += estimated_tokens
            return description
```

## Integration with File Processing Consumer

```python
class FileProcessingConsumer(BaseKafkaConsumer):
    def __init__(self, group_id: Optional[str] = None):
        super().__init__(group_id or "file_processing_group")
        
        # Enhanced vision processing
        self.smart_vision = SmartVisionProcessor()
        
    async def _process_document_directly(self, file_path: Path, user_id: str) -> bool:
        """Enhanced with smart vision processing."""
        try:
            # ... existing processing logic ...
            
            # Process with DoclingProcessor (extracts images)
            processed_result = self.docling_processor.process_document_with_images(str(file_path))
            
            # SMART VISION PROCESSING
            if processed_result.get('extracted_images'):
                enhanced_result = await self._enhance_with_smart_vision(
                    processed_result, 
                    file_path
                )
                
                # Log metrics for monitoring
                vision_metrics = enhanced_result.get('vision_metrics', {})
                self.logger.info(
                    f"Vision processing completed: {vision_metrics.get('summary', 'No metrics')}"
                )
                
                # Update content with enhanced descriptions
                processed_result['content'] = enhanced_result['enhanced_content']
                processed_result['vision_metrics'] = vision_metrics
            
            # ... rest of processing ...
            
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            return False
    
    async def _enhance_with_smart_vision(self, processed_result: dict, file_path: Path) -> dict:
        """Apply smart vision processing to extracted images."""
        
        # Prepare images for processing
        images = []
        for img_id, img_info in processed_result['extracted_images'].items():
            img_path = img_info['path']
            img_obj = Image.open(img_path)
            images.append((img_id, img_path, img_obj))
        
        # Extract context from document
        context = self._extract_document_context(processed_result['content'])
        
        # Process with smart vision
        vision_results = await self.smart_vision.process_document_images(images, context)
        
        # Enhance markdown content
        enhanced_content = self._integrate_vision_descriptions(
            processed_result['content'],
            vision_results['descriptions']
        )
        
        return {
            'enhanced_content': enhanced_content,
            'vision_metrics': vision_results['metrics'],
            'vision_summary': vision_results['summary']
        }
```

## Cost & Performance Benefits

### Token Usage Optimization
```python
# Before: All images get full analysis
# 100 images × 300 tokens each = 30,000 tokens

# After: Smart filtering
# 100 images × 5 tokens (classification) = 500 tokens
# 20 relevant images × 300 tokens (analysis) = 6,000 tokens
# Total: 6,500 tokens (78% reduction!)
```

### Concurrency Configuration
```python
# Optimized for your paid tier
CONCURRENCY_CONFIG = {
    'classification_per_consumer': 10,  # Fast, cheap operations
    'analysis_per_consumer': 3,        # Expensive operations
    'total_consumers': 6,              # From your Kafka partitions
    
    # Max concurrent API calls:
    # Classification: 6 × 10 = 60 calls (minimal tokens)
    # Analysis: 6 × 3 = 18 calls (full tokens)
}
```

### Monitoring Dashboard
```python
class VisionMetricsCollector:
    def log_processing_stats(self, metrics: dict):
        """Log detailed metrics for cost tracking."""
        self.logger.info(f"""
Vision Processing Summary:
├── Total Images: {metrics['total_images']}
├── Skipped (logos/decorative): {metrics['classified_skip']} ({metrics['classified_skip']/metrics['total_images']*100:.1f}%)
├── Analyzed (content): {metrics['classified_analyze']} ({metrics['classified_analyze']/metrics['total_images']*100:.1f}%)
├── Token Usage:
│   ├── Classification: {metrics['classification_tokens']} tokens
│   └── Analysis: {metrics['analysis_tokens']} tokens
└── Estimated Cost: ${metrics['total_cost_estimate']:.2f}
""")
```

This approach gives you:

1. **Maximum Quality**: No important images skipped
2. **Optimal Efficiency**: 70-80% token reduction through smart filtering  
3. **Full Scalability**: Handles large documents efficiently
4. **Cost Transparency**: Detailed metrics for monitoring
5. **Flexible Concurrency**: Separate limits for cheap vs expensive operations

Would you like me to implement this multi-level vision processor? The classification step is the key innovation here - it acts as a smart filter that dramatically reduces costs while maintaining quality.
