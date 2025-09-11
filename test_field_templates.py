"""
Test script for field template system performance.
Creates a template for insurance documents and measures the speed improvement.
"""

import asyncio
import time
from pathlib import Path

from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.pipelines.structured_extraction.services.field_template_manager import FieldTemplateManager
from src.backend.doc_processing_system.pipelines.structured_extraction.core.prefect_tasks import structured_extraction_flow
from src.backend.doc_processing_system.pipelines.structured_extraction.config.settings import Settings


async def create_insurance_template():
    """Create a field template for insurance documents."""
    print("🔧 Creating field template for insurance documents...")
    
    try:
        conn = ConnectionManager()
        template_manager = FieldTemplateManager(conn)
        
        # Define insurance template fields
        insurance_fields = {
            "policy_holder_name": "required, extract the full name of the policy holder",
            "policy_number": "required, extract the policy identification number",
            "coverage_amount": "required, extract as currency amount",
            "effective_date": "required, format as YYYY-MM-DD",
            "expiry_date": "required, format as YYYY-MM-DD",
            "insurance_company": "required, extract the insurance company name",
            "premium_amount": "optional, extract as currency if mentioned",
            "deductible": "optional, extract deductible amount if mentioned"
        }
        
        success = await template_manager.create_template(
            user_id="test_user",
            classification="insurance_confirmation",
            fields=insurance_fields
        )
        
        if success:
            print("✅ Insurance template created successfully!")
            
            # Verify template exists
            has_template = template_manager.has_template("test_user", "insurance_confirmation")
            print(f"✅ Template verification: {'Found' if has_template else 'Not found'}")
            
            # Show generated schema
            schemas = template_manager.get_template_schema("test_user", "insurance_confirmation")
            print(f"📋 Generated {len(schemas)} field schemas:")
            for schema in schemas:
                print(f"   - {schema.field_name}: {schema.field_type} ({schema.category})")
            
        else:
            print("❌ Failed to create template")
            
        return success
        
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return False


async def test_performance_with_template():
    """Test extraction performance using field template."""
    print("\n🚀 Testing extraction performance WITH field template...")
    
    try:
        # Load sample insurance document
        sample_file = Path("data/temp/docling/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD_vision_enhanced.md")
        
        if not sample_file.exists():
            print("❌ Sample document not found")
            return None
            
        document_text = sample_file.read_text(encoding='utf-8')
        settings = Settings()
        
        # Run extraction with template
        start_time = time.time()
        
        result = await structured_extraction_flow(
            document_text=document_text,
            document_id="template_test_insurance",
            settings=settings,
            user_id="test_user"
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"⏱️  Total extraction time WITH template: {total_time:.2f} seconds")
        
        # Analyze results
        if hasattr(result, 'execution_timeline') and result.execution_timeline:
            discovery_time = 0
            extraction_time = 0
            
            for event in result.execution_timeline:
                if event.get('task') == 'Sequential Discovery':
                    if event.get('status') == 'started':
                        discovery_start = event.get('timestamp')
                    elif event.get('status') == 'completed':
                        discovery_end = event.get('timestamp')
                        discovery_time = discovery_end - discovery_start
                        
                elif event.get('task') == 'Data Extraction':
                    if event.get('status') == 'started':
                        extraction_start = event.get('timestamp')
                    elif event.get('status') == 'completed':
                        extraction_end = event.get('timestamp')
                        extraction_time = extraction_end - extraction_start
            
            print(f"   📊 Sequential Discovery: {discovery_time:.2f} seconds")
            print(f"   📊 Data Extraction: {extraction_time:.2f} seconds")
            
            # Check if template was used
            discovery_method = getattr(result, 'discovery_method', 'unknown')
            if discovery_method == 'template_based':
                print("   ✅ Template-based discovery was used!")
            else:
                print("   ⚠️  Standard discovery was used (template may not have worked)")
        
        return total_time
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_performance_without_template():
    """Test extraction performance WITHOUT field template (for comparison)."""
    print("\n🐌 Testing extraction performance WITHOUT field template...")
    
    try:
        # Temporarily remove template to test baseline
        conn = ConnectionManager()
        template_manager = FieldTemplateManager(conn)
        
        # Check if template exists and get it
        has_template_before = template_manager.has_template("comparison_user", "insurance_confirmation")
        
        # Load sample insurance document
        sample_file = Path("data/temp/docling/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD_vision_enhanced.md")
        
        if not sample_file.exists():
            print("❌ Sample document not found")
            return None
            
        document_text = sample_file.read_text(encoding='utf-8')
        settings = Settings()
        
        # Run extraction without template (using different user_id)
        start_time = time.time()
        
        result = await structured_extraction_flow(
            document_text=document_text,
            document_id="baseline_test_insurance", 
            settings=settings,
            user_id="comparison_user"  # User without template
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"⏱️  Total extraction time WITHOUT template: {total_time:.2f} seconds")
        
        return total_time
        
    except Exception as e:
        print(f"❌ Baseline test failed: {e}")
        return None


async def main():
    """Run the complete field template performance test."""
    print("🧪 Field Template Performance Test")
    print("=" * 50)
    
    # Step 1: Create template
    template_created = await create_insurance_template()
    
    if not template_created:
        print("❌ Cannot proceed without template")
        return
    
    # Step 2: Test with template
    with_template_time = await test_performance_with_template()
    
    # Step 3: Test without template for comparison
    without_template_time = await test_performance_without_template()
    
    # Step 4: Compare results
    if with_template_time and without_template_time:
        print("\n📊 PERFORMANCE COMPARISON")
        print("=" * 30)
        print(f"⏱️  WITH template:    {with_template_time:.2f} seconds")
        print(f"⏱️  WITHOUT template: {without_template_time:.2f} seconds")
        
        improvement = without_template_time - with_template_time
        percentage = (improvement / without_template_time) * 100
        
        print(f"🚀 Speed improvement: {improvement:.2f} seconds ({percentage:.1f}% faster)")
        
        if improvement > 30:  # If we save more than 30 seconds
            print("✅ SIGNIFICANT performance improvement achieved!")
        elif improvement > 10:
            print("✅ Good performance improvement achieved!")
        else:
            print("ℹ️  Modest performance improvement")
    else:
        print("❌ Could not complete performance comparison")


if __name__ == "__main__":
    asyncio.run(main())