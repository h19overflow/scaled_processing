"""
Test script for vision processing integration with DoclingProcessor.
Simple test to verify the modular architecture works correctly.
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_import():
    """Safely import modules with detailed error reporting."""
    logger.info("🔍 Starting safe import process...")
    
    try:
        logger.info("📦 Importing DoclingProcessor...")
        from src.backend.doc_processing_system.pipelines.document_processing.docling_processor import DoclingProcessor
        logger.info("✅ DoclingProcessor imported successfully")
        
        logger.info("📦 Importing VisionConfig...")
        from src.backend.doc_processing_system.pipelines.document_processing.utils import VisionConfig
        logger.info("✅ VisionConfig imported successfully")
        
        return DoclingProcessor, VisionConfig
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error(f"📍 Error details: {traceback.format_exc()}")
        raise
    except Exception as e:
        logger.error(f"💥 Unexpected error during import: {e}")
        logger.error(f"📍 Error details: {traceback.format_exc()}")
        raise


async def test_vision_integration():
    """Test the vision processing integration."""
    
    logger.info("🚀 Testing Vision Processing Integration")
    
    try:
        # Import modules safely
        DoclingProcessor, VisionConfig = safe_import()
        
        # Test 1: Check module imports
        logger.info("✅ Testing module imports...")
        try:
            from src.backend.doc_processing_system.pipelines.document_processing.utils import (
                VisionConfig, ImageClassifier, VisionAgent, MarkdownEnhancer, VisionProcessor
            )
            logger.info("   All modules imported successfully")
        except ImportError as e:
            logger.error(f"   Import failed: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False
        
        # Test 2: Check configuration
        logger.info("✅ Testing configuration...")
        try:
            config = VisionConfig()
            logger.info(f"   Config created: model={config.model_name}, vision_enabled={config.enable_vision_processing}")
        except Exception as e:
            logger.error(f"   Config failed: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False
        
        # Test 3: Initialize DoclingProcessor with vision
        logger.info("✅ Testing DoclingProcessor initialization...")
        try:
            # Test with vision disabled first (simpler)
            logger.info("   Initializing DoclingProcessor without vision...")
            processor_without_vision = DoclingProcessor(enable_vision=False)
            logger.info("   ✅ DoclingProcessor without vision initialized")
            
            # Test with vision enabled  
            logger.info("   Initializing DoclingProcessor with vision...")
            processor_with_vision = DoclingProcessor(enable_vision=True)
            logger.info("   ✅ DoclingProcessor with vision initialized")
            
        except Exception as e:
            logger.error(f"   DoclingProcessor initialization failed: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False
        
        # Test 4: Check if sample document exists
        sample_doc = Path("data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf")
        
        if sample_doc.exists():
            logger.info(f"✅ Testing document processing with sample: {sample_doc.name}")
            
            try:
                # Test processing without vision first (faster) - use async version
                logger.info("   Processing without vision...")
                result_no_vision = await processor_without_vision.process_document_with_vision(
                    str(sample_doc), 
                    "test_doc_no_vision"
                )
                logger.info(f"   ✅ No vision: {len(result_no_vision.content)} chars, {result_no_vision.page_count} pages")
                
                # Test processing with vision (slower, but shows full pipeline)
                logger.info("   Processing with vision AI...")
                result_with_vision = await processor_with_vision.process_document_with_vision(
                    str(sample_doc), 
                    "test_doc_123"
                )
                logger.info(f"   ✅ With vision: {len(result_with_vision.content)} chars, {result_with_vision.page_count} pages")
                
                # Compare results
                vision_enhancement = len(result_with_vision.content) - len(result_no_vision.content)
                logger.info(f"   📊 Vision enhancement: +{vision_enhancement} characters")
                
                if vision_enhancement > 0:
                    logger.info("   🎉 Vision processing successfully enhanced content!")
                else:
                    logger.info("   ℹ️  No vision enhancement (may be due to no images or classification)")
                
            except Exception as e:
                logger.error(f"   Document processing failed: {e}")
                logger.error(f"   Traceback: {traceback.format_exc()}")
                return False
        else:
            logger.info("   ℹ️  Sample document not found, skipping document processing test")
        
        logger.info("🎉 All tests passed! Vision processing integration is working.")
        return True
        
    except Exception as e:
        logger.error(f"💥 Test failed with error: {e}")
        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        return False


async def test_individual_components():
    """Test individual components in isolation."""
    
    logger.info("🔧 Testing Individual Components")
    
    try:
        # Import modules safely
        DoclingProcessor, VisionConfig = safe_import()
        
        # Test VisionConfig
        logger.info("✅ Testing VisionConfig...")
        config = VisionConfig()
        logger.info(f"   Model: {config.model_name}")
        logger.info(f"   Classification concurrency: {config.classification_concurrency}")
        logger.info(f"   Analysis concurrency: {config.analysis_concurrency}")
        
        # Test environment config
        config_env = VisionConfig.from_env()
        logger.info(f"   Environment config loaded: vision_enabled={config_env.enable_vision_processing}")
        
        # Test MarkdownEnhancer (no API calls needed)
        logger.info("✅ Testing MarkdownEnhancer...")
        from src.backend.doc_processing_system.pipelines.document_processing.utils import MarkdownEnhancer
        
        enhancer = MarkdownEnhancer()
        test_content = "# Test Document\n\n![Test Image](image_1)\n\nSome text."
        test_descriptions = {
            "1": {
                "description": "A chart showing sales data",
                "classification": {"action": "analyze", "confidence": 0.9}
            }
        }
        
        enhanced = enhancer.enhance_content(test_content, test_descriptions)
        logger.info(f"   Original: {len(test_content)} chars")
        logger.info(f"   Enhanced: {len(enhanced)} chars")
        logger.info(f"   Enhancement: {len(enhanced) - len(test_content)} chars added")
        
        logger.info("🎉 Component tests completed!")
        
    except Exception as e:
        logger.error(f"💥 Component test failed: {e}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        raise


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("VISION PROCESSING INTEGRATION TEST")
    logger.info("=" * 60)
    
    try:
        logger.info("🔄 Starting test suite...")
        
        # Test individual components first
        logger.info("📋 Phase 1: Testing individual components...")
        asyncio.run(test_individual_components())
        
        print()
        
        # Test full integration
        logger.info("📋 Phase 2: Testing full integration...")
        success = asyncio.run(test_vision_integration())
        
        if success:
            logger.info("=" * 60)
            logger.info("🎉 ALL TESTS PASSED - INTEGRATION SUCCESSFUL!")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("❌ TESTS FAILED")
            logger.error("=" * 60)
            return 1
            
    except KeyboardInterrupt:
        logger.warning("⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Test suite failed with unexpected error: {e}")
        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    logger.info("🚀 Starting vision processing test...")
    exit_code = main()
    logger.info(f"🏁 Test completed with exit code: {exit_code}")
    sys.exit(exit_code)