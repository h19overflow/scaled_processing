"""
Field template manager for user-defined extraction templates.
Allows users to specify field templates based on classification to bypass Sequential Discovery.
"""

import logging
from typing import Dict, Any, List, Optional

from ..models.schema import FieldSchema, ProgressiveSchema
from ....core_deps.database.connection_manager import ConnectionManager


class FieldTemplateManager:
    """Manages user-defined field templates for bypassing Sequential Discovery."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize field template manager."""
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        
        # In-memory template storage for now (could be moved to database later)
        self.templates = {}
        self._initialize_default_templates()

    async def create_template(
        self,
        user_id: str,
        classification: str,
        fields: Dict[str, str]
    ) -> bool:
        """Create a field template from user-friendly field definitions.
        
        Args:
            user_id: User identifier
            classification: Document classification (contract, invoice, etc.)
            fields: Dict of field_name -> description/requirements
            
        Example:
            fields = {
                "employee_name": "required",
                "salary": "required, extract as number with currency",
                "start_date": "required, format YYYY-MM-DD"
            }
        """
        try:
            # Convert user-friendly format to template format
            field_definitions = {}
            
            for field_name, requirements in fields.items():
                # Parse requirements
                is_required = "required" in requirements.lower()
                weight = 0.9 if is_required else 0.7
                
                field_definitions[field_name] = {
                    "requirements": requirements,
                    "weight": weight,
                    "required": is_required,
                    "description": requirements if requirements != "required" else f"Extract {field_name} information from the document"
                }
            
            # Store template in memory (key: user_id/classification)
            template_key = f"{user_id}/{classification}"
            self.templates[template_key] = {
                "fields": field_definitions,
                "template_mode": True,
                "user_id": user_id,
                "classification": classification
            }
            
            self.logger.info(f"Field template created for {user_id}/{classification} with {len(fields)} fields")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create template: {e}")
            return False

    def has_template(self, user_id: str, classification: str, user_preferences: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has a field template for the classification.
        
        Args:
            user_id: User identifier
            classification: Document classification
            user_preferences: Unused (kept for compatibility)
        """
        try:
            template_key = f"{user_id}/{classification}"
            return template_key in self.templates and self.templates[template_key].get("template_mode", False)
            
        except Exception as e:
            self.logger.error(f"Failed to check template existence: {e}")
            return False

    def get_template_schema(self, user_id: str, classification: str) -> List[FieldSchema]:
        """Convert user template to FieldSchema objects for extraction."""
        try:
            template_key = f"{user_id}/{classification}"
            if template_key not in self.templates:
                self.logger.warning(f"No template found for {user_id}/{classification}")
                return []
            
            template = self.templates[template_key]
            field_definitions = template.get("fields", {})
            
            if not field_definitions:
                self.logger.warning(f"No field definitions found for {user_id}/{classification}")
                return []
            
            field_schemas = []
            for field_name, field_info in field_definitions.items():
                description = field_info.get("description", f"Extract {field_name} information from the document")
                
                # Create FieldSchema
                field_schema = FieldSchema(
                    field_name=field_name,
                    field_type=self._infer_field_type(field_name, description),
                    description=description,
                    example_text=f"Sample {field_name} data",
                    category=self._categorize_field(field_name),
                    subcategory="template_based"
                )
                field_schemas.append(field_schema)
            
            self.logger.info(f"Generated {len(field_schemas)} FieldSchemas from template for {classification}")
            return field_schemas
            
        except Exception as e:
            self.logger.error(f"Failed to get template schema: {e}")
            return []

    def create_schema_from_template(self, user_id: str, classification: str, chunks: List) -> List[ProgressiveSchema]:
        """Create ProgressiveSchema results from template, bypassing discovery."""
        try:
            field_schemas = self.get_template_schema(user_id, classification)
            
            if not field_schemas:
                self.logger.error(f"No field schemas generated from template for {user_id}/{classification}")
                return []
            
            # Create single ProgressiveSchema with all template fields
            progressive_schema = ProgressiveSchema(
                discovered_fields=field_schemas,
                document_type=classification,
                confidence_level="high",  # Templates are high confidence
                chunk_coverage=len(chunks)  # Cover all chunks
            )
            
            self.logger.info(f"Created ProgressiveSchema from template: {len(field_schemas)} fields, confidence: high")
            return [progressive_schema]
            
        except Exception as e:
            self.logger.error(f"Failed to create schema from template: {e}")
            return []

    # HELPER FUNCTIONS
    def _initialize_default_templates(self):
        """Initialize some default templates for testing."""
        # Contract template for test_user
        self.templates["test_user/contract"] = {
            "fields": {
                "employee_name": {
                    "requirements": "required",
                    "weight": 0.9,
                    "required": True,
                    "description": "Extract employee_name information from the document"
                },
                "salary": {
                    "requirements": "required, extract as number with currency",
                    "weight": 0.9,
                    "required": True,
                    "description": "required, extract as number with currency"
                },
                "start_date": {
                    "requirements": "required, format YYYY-MM-DD",
                    "weight": 0.9,
                    "required": True,
                    "description": "required, format YYYY-MM-DD"
                },
                "benefits": {
                    "requirements": "Extract benefits information from the document",
                    "weight": 0.7,
                    "required": False,
                    "description": "Extract benefits information from the document"
                }
            },
            "template_mode": True,
            "user_id": "test_user",
            "classification": "contract"
        }
    
    def _infer_field_type(self, field_name: str, description: str) -> str:
        """Infer field type from field name and description."""
        field_name_lower = field_name.lower()
        description_lower = description.lower()
        
        if any(word in field_name_lower for word in ["name", "title", "company"]):
            return "text"
        elif any(word in field_name_lower for word in ["date", "time"]):
            return "date"
        elif any(word in field_name_lower for word in ["amount", "salary", "price", "cost"]):
            return "currency"
        elif any(word in field_name_lower for word in ["email"]):
            return "email"
        elif any(word in field_name_lower for word in ["phone", "mobile"]):
            return "phone"
        elif "number" in description_lower or "currency" in description_lower:
            return "currency"
        else:
            return "text"

    def _categorize_field(self, field_name: str) -> str:
        """Categorize field based on field name."""
        field_name_lower = field_name.lower()
        
        if any(word in field_name_lower for word in ["name", "title", "email", "phone"]):
            return "identity"
        elif any(word in field_name_lower for word in ["salary", "amount", "price", "cost"]):
            return "financial"
        elif any(word in field_name_lower for word in ["date", "time", "duration"]):
            return "temporal"
        elif any(word in field_name_lower for word in ["company", "organization"]):
            return "organizational"
        else:
            return "general"


async def main():
    """Test the field template manager functionality."""
    print("Testing FieldTemplateManager...")
    
    try:
        conn = ConnectionManager()
        template_manager = FieldTemplateManager(conn)
        
        # Test template creation
        test_fields = {
            "employee_name": "required",
            "salary": "required, extract as number with currency",
            "start_date": "required, format YYYY-MM-DD",
            "benefits": "optional, extract benefit details"
        }
        
        print("Creating template...")
        success = await template_manager.create_template(
            user_id="test_user",
            classification="contract",
            fields=test_fields
        )
        print(f"Template creation: {'✅' if success else '❌'}")
        
        # Test template existence
        has_template = template_manager.has_template("test_user", "contract")
        print(f"Template exists: {'✅' if has_template else '❌'}")
        
        # Test schema generation
        if has_template:
            schemas = template_manager.get_template_schema("test_user", "contract")
            print(f"Generated {len(schemas)} field schemas")
            for schema in schemas:
                print(f"  - {schema.field_name}: {schema.field_type} ({schema.category})")
        
        print("✅ FieldTemplateManager test completed")
        
    except Exception as e:
        print(f"❌ Error testing FieldTemplateManager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())