# Vision Processing Strategy - Concurrency & Rate Limiting

## Problem Statement
Integrating vision API calls for image descriptions while managing:
- API rate limits (Google Gemini Vision)
- Concurrent processing across multiple consumers  
- Cost optimization
- Scalability

## Current Architecture Context
- **6 partitions** for `document-received` topic
- **6 consumers** processing documents simultaneously
- **Images per document**: 5-100+ images (highly variable)

## Strategy Options

### Option 1: Embedded Async Processing (Recommended)
```python
class FileProcessingConsumer:
    def __init__(self):
        self.vision_agent = VisionAgent()
        # Rate limiter: max 5 concurrent vision calls per consumer
        self.vision_semaphore = asyncio.Semaphore(5)
    
    async def _process_document_with_vision(self, file_path, document_id):
        # Step 1: Extract document + images (fast)
        processed_result = self.docling_processor.process_document(file_path)
        
        # Step 2: Process images asynchronously (I/O bound)
        enhanced_content = await self._enhance_with_vision_async(
            processed_result.content, 
            extracted_images_path
        )
        
        # Step 3: Save enhanced content
        self.document_crud.update_content(document_id, enhanced_content)
```

**Concurrency Math:**
- 6 consumers × 5 vision calls = **30 max concurrent API calls**
- Manageable for most API tiers
- No additional topics/infrastructure needed

### Option 2: Dedicated Vision Processing Topic
```python
# Add new topic for vision processing
EventType.VISION_PROCESSING_REQUIRED = "vision-processing-required"

class FileProcessingConsumer:
    def _process_document_directly(self, file_path, user_id):
        # Process document normally
        processed_result = self.docling_processor.process_document(file_path)
        
        # Publish for vision processing
        self.vision_producer.send_vision_required({
            "document_id": document_id,
            "images_path": extracted_images_path,
            "content": processed_result.content
        })

class VisionProcessingConsumer:
    def __init__(self):
        # Dedicated rate limiting for vision processing
        self.rate_limiter = AsyncRateLimiter(requests_per_minute=50)
    
    async def process_vision_request(self, message):
        # Process all images for document asynchronously
        enhanced_content = await self._process_images_batch(message)
```

**Concurrency Math:**
- Dedicated consumer pool (2-3 consumers)
- Rate limiter controls API calls globally
- Better resource isolation

### Option 3: Hybrid - Vision Queue with Batch Processing
```python
class VisionBatchProcessor:
    def __init__(self):
        self.batch_size = 10  # Process images in batches
        self.max_concurrent_batches = 3
    
    async def process_document_images(self, document_id, images):
        # Batch images to avoid overwhelming API
        batches = [images[i:i+self.batch_size] for i in range(0, len(images), self.batch_size)]
        
        # Process batches with controlled concurrency
        results = await asyncio.gather(*[
            self._process_image_batch(batch) 
            for batch in batches
        ], return_exceptions=True)
```

## Recommended Implementation Plan

### Phase 1: Start with Option 1 (Embedded Async)
**Why:** Simplest to implement, no new infrastructure

```python
# Enhanced FileProcessingConsumer
class FileProcessingConsumer(BaseKafkaConsumer):
    def __init__(self, group_id: Optional[str] = None):
        super().__init__(group_id or "file_processing_group")
        
        # Initialize vision agent with rate limiting
        self.vision_agent = VisionAgent()
        self.vision_semaphore = asyncio.Semaphore(5)  # 5 concurrent per consumer
        
        # Track vision processing metrics
        self.vision_metrics = {
            "images_processed": 0,
            "api_calls_made": 0,
            "rate_limit_hits": 0
        }
    
    async def _process_document_directly(self, file_path: Path, user_id: str) -> bool:
        # Existing processing logic...
        
        # NEW: Async vision enhancement
        if self._should_process_vision(processed_result):
            enhanced_content = await self._enhance_with_vision(
                processed_result, 
                file_path
            )
            
            # Update document with enhanced content
            self.document_crud.update_content(document_id, enhanced_content)
```

### Rate Limiting Strategy
```python
class VisionAgent:
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-2.5-flash-image-preview"
        
        # Rate limiting (adjust based on your API tier)
        self.rate_limiter = AsyncRateLimiter(
            requests_per_minute=30,  # Conservative start
            burst_size=10
        )
    
    async def describe_image_with_rate_limit(self, image, context=""):
        async with self.rate_limiter:
            return await self._describe_image_async(image, context)
```

### Monitoring & Metrics
```python
# Add to existing metrics
vision_processing_metrics = {
    "total_images_processed": 0,
    "avg_processing_time_per_image": 0,
    "rate_limit_hits": 0,
    "api_errors": 0,
    "cost_tracking": 0
}
```

## Configuration Parameters

### Environment Variables
```env
# Vision API Configuration
VISION_MAX_CONCURRENT_PER_CONSUMER=5
VISION_RATE_LIMIT_PER_MINUTE=30
VISION_ENABLE_BATCH_PROCESSING=true
VISION_BATCH_SIZE=10

# Cost Controls
VISION_MAX_IMAGES_PER_DOCUMENT=50
VISION_SKIP_LARGE_IMAGES=true
VISION_MAX_IMAGE_SIZE_MB=5
```

### Runtime Controls
```python
class VisionProcessingConfig:
    max_concurrent_per_consumer: int = 5
    rate_limit_per_minute: int = 30
    enable_for_file_types: List[str] = [".pdf", ".docx"]
    skip_if_too_many_images: int = 100  # Skip docs with 100+ images
    max_image_size_mb: float = 5.0
```

## Testing Strategy

### Load Testing Scenarios
1. **Single large document** (100+ images)
2. **Multiple small documents** (5-10 images each)
3. **Rate limit simulation** (intentional overwhelming)
4. **API failure scenarios** (network issues, quota exceeded)

### Gradual Rollout
1. Start with rate limit = 10 requests/minute
2. Monitor API usage and costs
3. Gradually increase based on performance
4. Add failover mechanisms (skip vision if API unavailable)

## Cost Estimation
```
Scenario: 1000 documents/day, avg 20 images each
- 20,000 API calls/day
- Google Gemini pricing: ~$0.001 per image
- Daily cost: ~$20
- Monthly cost: ~$600
```

Would you like me to implement Option 1 (embedded async) first, or would you prefer to discuss the rate limiting strategy more?