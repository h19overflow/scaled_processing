"""
Configuration generation node.
"""

from typing import List, Dict, Any
import textwrap

try:
    import langextract as lx

    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False


    class Extraction:
        def __init__(self, extraction_class: str, extraction_text: str, attributes: Dict[str, Any]):
            self.extraction_class = extraction_class
            self.extraction_text = extraction_text
            self.attributes = attributes


    class ExampleData:
        def __init__(self, text: str, extractions: List[Extraction]):
            self.text = text
            self.extractions = extractions

from ..models.state import MultiAgentState
from ..models.schema import FieldSchema
from ..config.settings import Settings


def generate_config(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Generate langextract configuration directly from discovery results."""
    try:
        # Get all discovered fields from progressive results
        all_fields = []
        for result in state["progressive_results"]:
            all_fields.extend(result.discovered_fields)
        
        if not all_fields:
            raise ValueError("No fields discovered to generate config")
        
        # Limit to max fields and remove duplicates
        seen_names = set()
        unique_fields = []
        for field in all_fields:
            if field.field_name.lower() not in seen_names:
                seen_names.add(field.field_name.lower())
                unique_fields.append(field)
                
                if len(unique_fields) >= settings.extraction.max_fields:
                    break
        
        sample_text = state["document_text"][:1000]
        config = _create_config_from_fields(unique_fields, sample_text, settings.models.extraction_model)

        return {
            **state,
            "config": config,
            "status": "config_generated"
        }

    except Exception as e:
        return {
            **state,
            "error": f"Config generation failed: {str(e)}",
            "status": "error"
        }


def _create_config_from_fields(fields: List[FieldSchema], sample_text: str, model_id: str) -> Dict[str, Any]:
    """Create langextract configuration directly from discovered fields."""

    # Validate inputs
    if not fields:
        raise ValueError("Cannot create config from empty fields list")
    
    if not sample_text or len(sample_text.strip()) < 10:
        sample_text = "Sample document text for extraction demonstration purposes."
    
    if not model_id or len(model_id.strip()) == 0:
        raise ValueError("Model ID cannot be empty")

    # Create field list with validation
    field_list = _format_field_list(fields)
    
    # Create extraction prompt
    prompt = textwrap.dedent(f"""
        Extract structured information from this document.
        
        Extract the following types of information:
        {field_list}
        
        IMPORTANT RULES:
        - Use exact text from the document for extractions
        - Only extract information that actually exists in the document
        - If information is not found, skip that extraction class
        - Provide meaningful attributes for context
        - Do not create empty or duplicate extractions
    """).strip()

    # Validate final prompt
    if len(prompt.strip()) < 50:
        raise ValueError("Generated prompt is too short - configuration may be invalid")

    # Create example data
    examples = _create_examples(fields, sample_text)

    return {
        "prompt": prompt,
        "examples": examples,
        "model_id": model_id.strip(),
        "extraction_classes": [field.field_name for field in fields]
    }


def _create_config(schema, sample_text: str, model_id: str) -> Dict[str, Any]:
    """Create langextract configuration from schema."""

    # Create extraction prompt
    prompt = textwrap.dedent(f"""
        {schema.extraction_prompt}
        
        Extract the following types of information:
        {_format_extraction_classes(schema.extraction_classes)}
        
        IMPORTANT RULES:
        - Use exact text from the document for extractions
        - Only extract information that actually exists in the document
        - If information is not found, skip that extraction class
        - Provide meaningful attributes for context
        - Do not create empty or duplicate extractions
    """).strip()

    # Create example data
    examples = _create_examples(schema.extraction_classes, sample_text)

    return {
        "prompt": prompt,
        "examples": examples,
        "model_id": model_id,
        "extraction_classes": [field.field_name for field in schema.extraction_classes]
    }


def _format_field_list(fields: List[FieldSchema]) -> str:
    """Format field list for prompt."""
    formatted = []
    for field in fields:
        # Ensure description is not empty
        description = field.description if field.description and field.description.strip() else f"Extract {field.field_name} information from the document"
        formatted.append(f"- {field.field_name}: {description}")
    
    # Ensure we have at least some content
    if not formatted:
        formatted.append("- general_information: Extract any relevant information from the document")
    
    return "\n".join(formatted)


def _format_extraction_classes(classes: List[FieldSchema]) -> str:
    """Format extraction classes for prompt."""
    formatted = []
    for field in classes:
        # Ensure description is not empty
        description = field.description if field.description and field.description.strip() else f"Extract {field.field_name} information from the document"
        formatted.append(f"- {field.field_name}: {description}")
    
    # Ensure we have at least some content
    if not formatted:
        formatted.append("- general_information: Extract any relevant information from the document")
    
    return "\n".join(formatted)


def _create_examples(extraction_classes: List[FieldSchema], sample_text: str) -> List:
    """Create example extractions using document text."""
    if not sample_text:
        sample_text = "Sample document text for demonstration."

    # Create one extraction per class
    extractions = []
    for field in extraction_classes:
        example_text = field.example_text if field.example_text else f"Sample {field.field_name}"
        attributes = {"category": field.category, "subcategory": field.subcategory}

        if LANGEXTRACT_AVAILABLE:
            extraction = lx.data.Extraction(
                extraction_class=field.field_name,
                extraction_text=example_text,
                attributes=attributes
            )
        else:
            extraction = Extraction(
                extraction_class=field.field_name,
                extraction_text=example_text,
                attributes=attributes
            )
        extractions.append(extraction)

    # Use longer sample text for better alignment
    example_text = sample_text[:1500] if len(sample_text) > 1500 else sample_text

    # Create example data
    if LANGEXTRACT_AVAILABLE:
        example = lx.data.ExampleData(
            text=example_text,
            extractions=extractions
        )
    else:
        example = ExampleData(
            text=example_text,
            extractions=extractions
        )

    return [example]


async def demonstrate_config_generation():
    """
    Demonstrate how configuration generation works with template-based discovery.
    Shows the complete flow from template → FieldSchema → Config → AI Prompt.
    """
    import json
    import os
    from pathlib import Path
    from ..services.field_template_manager import FieldTemplateManager
    from ....core_deps.database.connection_manager import ConnectionManager
    from ..config.settings import Settings
    
    print("🧪 Configuration Generation Demonstration")
    print("=" * 50)
    
    # Initialize components
    conn = ConnectionManager()
    template_manager = FieldTemplateManager(conn)
    settings = Settings()
    
    # Step 1: Get template schema for contract classification
    print("📋 Step 1: Getting template schema for test_user/contract")
    field_schemas = template_manager.get_template_schema("test_user", "contract")
    
    if not field_schemas:
        print("❌ No template found for test_user/contract")
        return
    
    print(f"✅ Found {len(field_schemas)} fields in template:")
    for i, field in enumerate(field_schemas, 1):
        print(f"   {i}. {field.field_name}: {field.field_type} ({field.category})")
        print(f"      Description: {field.description}")
    
    # Step 2: Create sample contract document text
    print("\n📄 Step 2: Sample contract document")
    sample_contract = """
    EMPLOYMENT CONTRACT
    
    This Employment Agreement is entered into between TechCorp Industries and John Smith.
    
    Employee Information:
    Name: John Smith
    Position: Senior Software Engineer
    Start Date: January 15, 2024
    
    Compensation:
    Annual Salary: $95,000
    
    Company Information:
    TechCorp Industries
    123 Business Ave, Tech City, TC 12345
    
    Benefits:
    - Health insurance coverage
    - 401(k) retirement plan with company matching
    - 15 days paid vacation annually
    
    This contract is effective from January 15, 2024.
    """
    
    print("✅ Sample contract created (abbreviated)")
    print(f"   Length: {len(sample_contract)} characters")
    
    # Step 3: Generate configuration
    print("\n⚙️ Step 3: Generating extraction configuration")
    
    try:
        config = _create_config_from_fields(
            fields=field_schemas,
            sample_text=sample_contract,
            model_id=settings.models.extraction_model
        )
        
        print("✅ Configuration generated successfully!")
        print(f"   Model: {config['model_id']}")
        print(f"   Extraction classes: {len(config['extraction_classes'])}")
        print(f"   Examples: {len(config['examples'])}")
        
        # Step 4: Show the generated prompt
        print("\n🤖 Step 4: Generated AI Prompt")
        print("-" * 40)
        print(config['prompt'])
        print("-" * 40)
        
        # Step 5: Show example extractions
        print("\n📝 Step 5: Example extractions for training")
        for i, example in enumerate(config['examples'], 1):
            print(f"Example {i}:")
            print(f"   Text length: {len(example.text)} characters")
            print(f"   Extractions: {len(example.extractions)}")
            for extraction in example.extractions:
                print(f"     - {extraction.extraction_class}: {extraction.extraction_text}")
                print(f"       Attributes: {extraction.attributes}")
        
        # Step 6: Save results to demo_results
        print("\n💾 Step 6: Saving results to demo_results/")
        
        # Create demo_results directory if it doesn't exist
        demo_dir = Path("demo_results")
        demo_dir.mkdir(exist_ok=True)
        
        # Prepare data for JSON serialization
        config_data = {
            "demonstration_info": {
                "user_id": "test_user",
                "classification": "contract",
                "template_fields_count": len(field_schemas),
                "sample_document_length": len(sample_contract),
                "model_used": config['model_id']
            },
            "template_fields": [
                {
                    "field_name": field.field_name,
                    "field_type": field.field_type,
                    "description": field.description,
                    "category": field.category,
                    "subcategory": field.subcategory,
                    "example_text": field.example_text
                }
                for field in field_schemas
            ],
            "generated_config": {
                "model_id": config['model_id'],
                "extraction_classes": config['extraction_classes'],
                "prompt": config['prompt']
            },
            "sample_document": sample_contract,
            "example_extractions": [
                {
                    "text_preview": example.text[:200] + "..." if len(example.text) > 200 else example.text,
                    "extractions": [
                        {
                            "extraction_class": ext.extraction_class,
                            "extraction_text": ext.extraction_text,
                            "attributes": ext.attributes
                        }
                        for ext in example.extractions
                    ]
                }
                for example in config['examples']
            ]
        }
        
        # Save to file
        output_file = demo_dir / "config_generation_example.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Results saved to: {output_file}")
        
        # Step 7: Analysis and insights
        print("\n🔍 Step 7: Configuration Analysis")
        print("Template Priority Integration:")
        
        required_fields = [f for f in field_schemas if "required" in f.description.lower()]
        optional_fields = [f for f in field_schemas if "optional" in f.description.lower()]
        
        print(f"   📌 Required fields: {len(required_fields)}")
        for field in required_fields:
            print(f"      - {field.field_name}: {field.description}")
        
        print(f"   📝 Optional fields: {len(optional_fields)}")
        for field in optional_fields:
            print(f"      - {field.field_name}: {field.description}")
        
        print("\n✅ Configuration generation demonstration completed!")
        print(f"📁 Check {output_file} for detailed results")
        
        return config_data
        
    except Exception as e:
        print(f"❌ Configuration generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_actual_extraction():
    """
    Test actual extraction using the generated configuration on the sample contract.
    This shows what the real extraction results would look like.
    """
    import json
    from pathlib import Path
    from ..core.prefect_tasks import structured_extraction_flow
    from ..config.settings import Settings
    
    print("\n🔬 Testing Actual Extraction Results")
    print("=" * 50)
    
    # Sample contract document
    sample_contract = """
    EMPLOYMENT CONTRACT
    
    This Employment Agreement is entered into between TechCorp Industries and John Smith.
    
    Employee Information:
    Name: John Smith
    Position: Senior Software Engineer
    Start Date: January 15, 2024
    
    Compensation:
    Annual Salary: $95,000
    
    Company Information:
    TechCorp Industries
    123 Business Ave, Tech City, TC 12345
    
    Benefits:
    - Health insurance coverage
    - 401(k) retirement plan with company matching
    - 15 days paid vacation annually
    
    This contract is effective from January 15, 2024.
    """
    
    print("📋 Running full extraction pipeline with contract template...")
    print(f"   Document length: {len(sample_contract)} characters")
    print(f"   User: test_user")
    print(f"   Expected classification: contract")
    
    try:
        settings = Settings()
        
        # Run the complete pipeline
        result = await structured_extraction_flow(
            document_text=sample_contract,
            document_id="contract_extraction_test",
            settings=settings,
            user_id="test_user"  # This user has contract template
        )
        
        print(f"\n✅ Pipeline completed with status: {result.status}")
        print(f"🔍 Classification: {getattr(result, 'classification', 'unknown')}")
        print(f"⚡ Discovery method: {getattr(result, 'discovery_method', 'unknown')}")
        
        if hasattr(result, 'extractions') and result.extractions:
            print(f"\n📊 Extraction Results ({len(result.extractions)} items):")
            for i, extraction in enumerate(result.extractions, 1):
                extraction_class = extraction.get('extraction_class', 'unknown')
                extraction_text = extraction.get('extraction_text', 'N/A')
                attributes = extraction.get('attributes', {})
                
                print(f"   {i}. {extraction_class}: '{extraction_text}'")
                print(f"      Category: {attributes.get('category', 'N/A')}")
                print(f"      Subcategory: {attributes.get('subcategory', 'N/A')}")
        else:
            print("\n❌ No extractions found!")
            
        # Get full observability data
        print("\n🔍 Gathering full observability data...")
        
        # Get user preferences and template details
        from ..services.preference_manager import PreferenceManager
        preference_manager = PreferenceManager(conn)
        
        user_preferences = preference_manager.get_user_preferences("test_user", "contract")
        template_schemas = template_manager.get_template_schema("test_user", "contract")
        
        # Save as structured markdown
        demo_dir = Path("demo_results")
        demo_dir.mkdir(exist_ok=True)
        
        # Create comprehensive markdown report
        markdown_content = self._create_markdown_report(
            result=result,
            sample_contract=sample_contract,
            user_preferences=user_preferences,
            template_schemas=template_schemas,
            config=config if 'config' in locals() else None
        )
        
        output_file = demo_dir / "extraction_analysis_report.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"\n📋 Full analysis report saved to: {output_file}")
        
        # Also save JSON backup for programmatic access
        actual_results = {
            "test_info": {
                "user_id": "test_user",
                "document_id": "contract_extraction_test",
                "document_length": len(sample_contract),
                "pipeline_status": result.status,
                "discovery_method": getattr(result, 'discovery_method', 'unknown'),
                "classification": getattr(result, 'classification', 'unknown')
            },
            "user_preferences": user_preferences,
            "template_schemas": [
                {
                    "field_name": schema.field_name,
                    "field_type": schema.field_type,
                    "description": schema.description,
                    "category": schema.category,
                    "subcategory": schema.subcategory,
                    "example_text": schema.example_text
                }
                for schema in template_schemas
            ],
            "sample_document": sample_contract,
            "actual_extractions": result.extractions if hasattr(result, 'extractions') else [],
            "template_used": getattr(result, 'discovery_method', 'unknown') == 'template_based'
        }
        
        json_output_file = demo_dir / "extraction_analysis_data.json"
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(actual_results, f, indent=2, ensure_ascii=False)
        
        print(f"📊 JSON data backup saved to: {json_output_file}")
        
        # Analysis
        if hasattr(result, 'extractions') and result.extractions:
            print(f"\n🎯 Extraction Quality Analysis:")
            
            expected_fields = ["employee_name", "salary", "start_date", "benefits"]
            found_fields = [ext.get('extraction_class') for ext in result.extractions]
            
            for field in expected_fields:
                if field in found_fields:
                    extraction = next(ext for ext in result.extractions if ext.get('extraction_class') == field)
                    text = extraction.get('extraction_text', '')
                    
                    if field == "employee_name":
                        quality = "✅ Good" if "john" in text.lower() or "smith" in text.lower() else "❌ Poor"
                    elif field == "salary":
                        quality = "✅ Good" if "$" in text and "95" in text else "❌ Poor"
                    elif field == "start_date":
                        quality = "✅ Good" if "2024" in text and "01" in text else "❌ Poor"
                    elif field == "benefits":
                        quality = "✅ Good" if "insurance" in text.lower() or "401" in text else "❌ Poor"
                    else:
                        quality = "❓ Unknown"
                        
                    print(f"   {field}: {quality} - '{text}'")
                else:
                    print(f"   {field}: ❌ Missing")
        
        return actual_results
        
    except Exception as e:
        print(f"❌ Actual extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # First run the configuration demo
        await demonstrate_config_generation()
        
        # Then test actual extraction
        await test_actual_extraction()
    
    asyncio.run(main())
