"""
Component Use Case Tester for Structured Extraction Pipeline.

Tests each component and node separately with real use cases,
saving outputs to example_outputs directory for analysis.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..config.settings import Settings
from ..models.state import MultiAgentState
from ..nodes.chunking import chunk_document
from ..nodes.classification import classify_document
from ..nodes.config_gen import generate_config
from ..nodes.consolidation import consolidate_schema
from ..nodes.context_loading import load_feedback_context
from ..nodes.discovery import sequential_discovery
from ..nodes.extraction import extract_data
from ..nodes.preference_injection import inject_user_preferences
from ..services.classification_service import DocumentClassificationService
from ..services.feedback_context_manager import FeedbackContextManager
from ..services.preference_manager import PreferenceManager
from ....core_deps.database.CRUD.classification_crud import ClassificationCRUD
from ....core_deps.database.CRUD.feedback_crud import FeedbackCRUD
from ....core_deps.database.CRUD.preferences_crud import PreferencesCRUD
from ....core_deps.database.connection_manager import ConnectionManager


class ComponentUseCaseTester:
    """Test individual components with real use cases."""

    def __init__(self):
        """Initialize tester with output directory."""
        self.output_dir = os.path.join(os.path.dirname(__file__), "example_outputs")
        os.makedirs(self.output_dir, exist_ok=True)

        self.connection_manager = ConnectionManager()
        self.settings = Settings()
        self.logger = logging.getLogger(__name__)

        # Initialize CRUD operations
        self.preferences_crud = PreferencesCRUD(self.connection_manager)
        self.feedback_crud = FeedbackCRUD(self.connection_manager)
        self.classification_crud = ClassificationCRUD(self.connection_manager)

        # Sample documents for testing
        self.sample_documents = {
            "contract": """
            EMPLOYMENT AGREEMENT
            
            This Employment Agreement is entered into between TechCorp Inc. ("Company") 
            and John Smith ("Employee") on January 15, 2024.
            
            POSITION: Software Engineer
            SALARY: $75,000 annually
            START DATE: February 1, 2024
            
            RESPONSIBILITIES:
            - Develop and maintain web applications
            - Collaborate with cross-functional teams
            - Participate in code reviews
            
            BENEFITS:
            - Health insurance coverage
            - 401(k) retirement plan
            - 20 days paid vacation
            """,

            "invoice": """
            INVOICE #INV-2024-001
            
            From: ABC Services LLC
            123 Business St, City, ST 12345
            Tax ID: 12-3456789
            
            To: XYZ Corporation
            456 Corporate Ave, City, ST 67890
            
            Date: March 15, 2024
            Due Date: April 15, 2024
            
            SERVICES:
            - Consulting Services (40 hours @ $150/hr): $6,000.00
            - Project Management (20 hours @ $125/hr): $2,500.00
            
            Subtotal: $8,500.00
            Tax (8.5%): $722.50
            Total Amount: $9,222.50
            """,

            "medical": """
            PATIENT MEDICAL RECORD
            
            Patient: Jane Doe
            DOB: 05/12/1985
            Patient ID: P123456
            Visit Date: April 10, 2024
            
            CHIEF COMPLAINT: Annual physical examination
            
            VITAL SIGNS:
            - Blood Pressure: 120/80 mmHg
            - Heart Rate: 72 bpm
            - Temperature: 98.6°F
            - Weight: 140 lbs
            
            ASSESSMENT:
            Patient in good health. All vital signs normal.
            Recommend annual blood work and mammogram.
            
            MEDICATIONS:
            - Multivitamin daily
            - Continue current exercise routine
            """
        }

    async def setup_test_data(self) -> None:
        """Populate database with sample data for testing."""
        self.logger.info("Setting up test data in database...")

        try:
            # Create sample user preferences for each document type
            await self._create_sample_preferences()

            # Create sample feedback data
            await self._create_sample_feedback()

            # Create sample classification data
            await self._create_sample_classifications()

            self.logger.info("Test data setup completed!")

        except Exception as e:
            self.logger.error(f"Failed to setup test data: {e}")
            raise

    async def _create_sample_preferences(self) -> None:
        """Create sample user preferences."""
        preferences_data = {
            "contract": {
                "field_preferences": {
                    "field_priorities": {
                        "employee_name": {"weight": 0.9, "required": True},
                        "company_name": {"weight": 0.9, "required": True},
                        "position": {"weight": 0.8, "required": True},
                        "salary": {"weight": 0.9, "required": True},
                        "start_date": {"weight": 0.8, "required": True},
                        "benefits": {"weight": 0.6, "required": False}
                    },
                    "extraction_rules": {
                        "salary": "Extract as numerical value with currency",
                        "dates": "Format as YYYY-MM-DD"
                    }
                },
                "extraction_style": {
                    "verbosity": "detailed",
                    "confidence_threshold": 0.8,
                    "context_awareness": True,
                    "cross_reference": True
                },
                "prompt_instructions": "Focus on employment terms and legal obligations"
            },

            "invoice": {
                "field_preferences": {
                    "field_priorities": {
                        "invoice_number": {"weight": 0.9, "required": True},
                        "total_amount": {"weight": 0.9, "required": True},
                        "due_date": {"weight": 0.8, "required": True},
                        "vendor_info": {"weight": 0.7, "required": True},
                        "line_items": {"weight": 0.8, "required": False},
                        "tax_amount": {"weight": 0.7, "required": False}
                    },
                    "extraction_rules": {
                        "amounts": "Extract as numerical values with currency",
                        "dates": "Format as YYYY-MM-DD",
                        "line_items": "Extract as structured list"
                    }
                },
                "extraction_style": {
                    "verbosity": "standard",
                    "confidence_threshold": 0.8,
                    "context_awareness": True
                },
                "prompt_instructions": "Focus on financial data and billing information"
            },

            "medical": {
                "field_preferences": {
                    "field_priorities": {
                        "patient_name": {"weight": 0.9, "required": True},
                        "patient_id": {"weight": 0.8, "required": True},
                        "visit_date": {"weight": 0.8, "required": True},
                        "vital_signs": {"weight": 0.8, "required": False},
                        "diagnosis": {"weight": 0.9, "required": False},
                        "medications": {"weight": 0.7, "required": False}
                    },
                    "extraction_rules": {
                        "vital_signs": "Extract as structured measurements",
                        "dates": "Format as YYYY-MM-DD",
                        "medications": "Extract as list with dosages"
                    }
                },
                "extraction_style": {
                    "verbosity": "detailed",
                    "confidence_threshold": 0.8,
                    "context_awareness": True
                },
                "prompt_instructions": "Focus on medical data with attention to accuracy"
            }
        }

        for classification, prefs in preferences_data.items():
            self.preferences_crud.create_or_update_preferences(
                user_id="test_user",
                classification=classification,
                field_preferences=prefs["field_preferences"],
                extraction_style=prefs["extraction_style"],
                prompt_instructions=prefs["prompt_instructions"]
            )
            self.logger.info(f"Created preferences for {classification}")

    # TODO missmatch between create_or_update_preferences definition and usage , in the db there is no field_name.
    async def _create_sample_feedback(self) -> None:
        """Create sample feedback data."""
        feedback_data = [
            {
                "user_id": "test_user",
                "document_id": "doc_001",
                "classification": "contract",
                "feedback_type": "field_missing",
                "field_name": "termination_clause",
                "feedback_text": "Missing termination clause information",
                "quality_rating": 3,
                "suggestions": "Please extract termination conditions when available"
            },
            {
                "user_id": "test_user",
                "document_id": "doc_002",
                "classification": "invoice",
                "feedback_type": "field_incorrect",
                "field_name": "total_amount",
                "feedback_text": "Total amount extracted incorrectly",
                "quality_rating": 2,
                "suggestions": "Include tax in total calculation"
            },
            {
                "user_id": "test_user",
                "document_id": "doc_003",
                "classification": "medical",
                "feedback_type": "extraction_quality",
                "field_name": "vital_signs",
                "feedback_text": "Good extraction of vital signs",
                "quality_rating": 5,
                "suggestions": "Continue current approach for medical data"
            },
            {
                "user_id": "test_user",
                "document_id": "doc_004",
                "classification": "contract",
                "feedback_type": "field_format",
                "field_name": "salary",
                "feedback_text": "Salary format needs improvement",
                "quality_rating": 3,
                "suggestions": "Extract salary as structured amount with currency"
            }
        ]

        for feedback in feedback_data:
            self.feedback_crud.create_feedback(**feedback)
            self.logger.info(f"Created feedback for {feedback['classification']}")

    async def _create_sample_classifications(self) -> None:
        """Create sample classification records."""
        classifications = [
            {
                "document_id": "sample_contract_001",
                "user_id": "test_user",
                "classification": "contract",
                "confidence_score": 0.95,
                "classification_method": "llm",
                "keywords_found": ["agreement", "employee", "salary", "benefits"]
            },
            {
                "document_id": "sample_invoice_001",
                "user_id": "test_user",
                "classification": "invoice",
                "confidence_score": 0.92,
                "classification_method": "llm",
                "keywords_found": ["invoice", "payment", "total", "due date"]
            },
            {
                "document_id": "sample_medical_001",
                "user_id": "test_user",
                "classification": "medical",
                "confidence_score": 0.88,
                "classification_method": "keyword",
                "keywords_found": ["patient", "diagnosis", "treatment", "medical"]
            }
        ]

        for classification in classifications:
            self.classification_crud.create_classification(**classification)
            self.logger.info(f"Created classification for {classification['classification']}")

    async def cleanup_test_data(self) -> None:
        """Clean up test data from database."""
        self.logger.info("Cleaning up test data...")

        try:
            # Note: Add cleanup methods based on your CRUD implementations
            # This is a placeholder - implement based on available delete methods
            self.logger.info("Test data cleanup completed!")

        except Exception as e:
            self.logger.warning(f"Failed to cleanup test data: {e}")

    def save_output(self, component: str, test_case: str, data: Any) -> str:
        """Save component output to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{component}_{test_case}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Convert to JSON-serializable format
        if hasattr(data, '__dict__'):
            data = data.__dict__
        elif isinstance(data, dict):
            data = self._clean_dict_for_json(data)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

        self.logger.info(f"Saved {component} output to {filename}")
        return filepath

    def _clean_dict_for_json(self, obj: Any) -> Any:
        """Clean dictionary for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._clean_dict_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_dict_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._clean_dict_for_json(obj.__dict__)
        else:
            return obj

    async def test_classification_service(self) -> None:
        """Test document classification service."""
        self.logger.info("Testing Classification Service...")

        service = DocumentClassificationService(self.connection_manager)

        for doc_type, content in self.sample_documents.items():
            doc_id = str(uuid4())
            user_id = "test_user"

            try:
                result = await service.classify_document(
                    document_text=content,
                    document_id=doc_id,
                    user_id=user_id
                )

                test_data = {
                    "component": "classification_service",
                    "input": {
                        "document_type": doc_type,
                        "document_id": doc_id,
                        "text_preview": content[:200] + "..."
                    },
                    "output": result,
                    "success": True
                }

                self.save_output("classification_service", doc_type, test_data)

            except Exception as e:
                error_data = {
                    "component": "classification_service",
                    "document_type": doc_type,
                    "error": str(e),
                    "success": False
                }
                self.save_output("classification_service", f"{doc_type}_error", error_data)

    async def test_preference_manager(self) -> None:
        """Test preference manager service."""
        self.logger.info("Testing Preference Manager...")

        manager = PreferenceManager(self.connection_manager)

        # Test getting preferences
        for classification in ["contract", "invoice", "medical"]:
            try:
                preferences = await manager.get_user_preferences("test_user", classification)

                test_data = {
                    "component": "preference_manager",
                    "operation": "get_preferences",
                    "input": {"classification": classification},
                    "output": preferences,
                    "success": True
                }

                self.save_output("preference_manager", f"get_{classification}", test_data)

            except Exception as e:
                error_data = {
                    "component": "preference_manager",
                    "operation": "get_preferences",
                    "classification": classification,
                    "error": str(e),
                    "success": False
                }
                self.save_output("preference_manager", f"get_{classification}_error", error_data)

        # Test preference prompt injection
        try:
            sample_preferences = {
                "field_preferences": {
                    "field_priorities": {
                        "amount": {"weight": 0.9, "required": True},
                        "date": {"weight": 0.8, "required": True}
                    }
                },
                "extraction_style": {
                    "verbosity": "detailed",
                    "confidence_threshold": 0.8
                },
                "prompt_instructions": "Focus on financial data extraction"
            }

            prompt_injection = manager.generate_preference_prompt_injection(sample_preferences)

            test_data = {
                "component": "preference_manager",
                "operation": "prompt_injection",
                "input": sample_preferences,
                "output": {"prompt_text": prompt_injection},
                "success": True
            }

            self.save_output("preference_manager", "prompt_injection", test_data)

        except Exception as e:
            error_data = {
                "component": "preference_manager",
                "operation": "prompt_injection",
                "error": str(e),
                "success": False
            }
            self.save_output("preference_manager", "prompt_injection_error", error_data)

    async def test_feedback_context_manager(self) -> None:
        """Test feedback context manager."""
        self.logger.info("Testing Feedback Context Manager...")

        manager = FeedbackContextManager(self.connection_manager)

        for classification in ["contract", "invoice", "medical"]:
            try:
                context = await manager.get_feedback_context(
                    classification=classification,
                    user_id="test_user",
                    limit=3
                )

                test_data = {
                    "component": "feedback_context_manager",
                    "input": {"classification": classification},
                    "output": context,
                    "success": True
                }

                self.save_output("feedback_context_manager", classification, test_data)

            except Exception as e:
                error_data = {
                    "component": "feedback_context_manager",
                    "classification": classification,
                    "error": str(e),
                    "success": False
                }
                self.save_output("feedback_context_manager", f"{classification}_error", error_data)

    async def test_nodes(self) -> None:
        """Test individual pipeline nodes."""
        self.logger.info("Testing Pipeline Nodes...")

        for doc_type, content in self.sample_documents.items():
            # Create initial state
            state = MultiAgentState(
                document_text=content,
                document_id=str(uuid4()),
                user_id="test_user",
                chunks=[],
                progressive_results=[],
                consolidated_schema=None,
                final_schema=None,
                config=None,
                extractions=[],
                status="started",
                error="",
                classification=None,
                classification_confidence=None,
                feedback_context=None,
                user_preferences=None
            )

            # Test each node in sequence
            await self.test_classification_node(state, doc_type)
            await self.test_context_loading_node(state, doc_type)
            await self.test_preference_injection_node(state, doc_type)
            await self.test_chunking_node(state, doc_type)
            await self.test_discovery_node(state, doc_type)
            await self.test_consolidation_node(state, doc_type)
            await self.test_config_generation_node(state, doc_type)
            await self.test_extraction_node(state, doc_type)

    async def test_classification_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test classification node."""
        try:
            result = await classify_document(state)

            test_data = {
                "component": "classification_node",
                "document_type": doc_type,
                "input_state_keys": list(state.keys()) if hasattr(state, 'keys') else [],
                "output": result,
                "success": True
            }

            self.save_output("classification_node", doc_type, test_data)

            # Update state for next tests
            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "classification_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("classification_node", f"{doc_type}_error", error_data)

    async def test_context_loading_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test context loading node."""
        try:
            result = await load_feedback_context(state)

            test_data = {
                "component": "context_loading_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("context_loading_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "context_loading_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("context_loading_node", f"{doc_type}_error", error_data)

    async def test_preference_injection_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test preference injection node."""
        try:
            result = await inject_user_preferences(state)

            test_data = {
                "component": "preference_injection_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("preference_injection_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "preference_injection_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("preference_injection_node", f"{doc_type}_error", error_data)

    async def test_chunking_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test document chunking node."""
        try:
            result = chunk_document(state, self.settings)

            test_data = {
                "component": "chunking_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("chunking_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "chunking_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("chunking_node", f"{doc_type}_error", error_data)

    async def test_discovery_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test sequential discovery node."""
        try:
            result = await sequential_discovery(state, self.settings)

            test_data = {
                "component": "discovery_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("discovery_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "discovery_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("discovery_node", f"{doc_type}_error", error_data)

    async def test_consolidation_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test schema consolidation node."""
        try:
            result = await consolidate_schema(state, self.settings)

            test_data = {
                "component": "consolidation_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("consolidation_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "consolidation_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("consolidation_node", f"{doc_type}_error", error_data)

    async def test_config_generation_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test config generation node."""
        try:
            result = await generate_config(state, self.settings)

            test_data = {
                "component": "config_generation_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("config_generation_node", doc_type, test_data)

            if isinstance(result, dict):
                state.update(result)

        except Exception as e:
            error_data = {
                "component": "config_generation_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("config_generation_node", f"{doc_type}_error", error_data)

    async def test_extraction_node(self, state: MultiAgentState, doc_type: str) -> None:
        """Test data extraction node."""
        try:
            result = await extract_data(state, self.settings)

            test_data = {
                "component": "extraction_node",
                "document_type": doc_type,
                "output": result,
                "success": True
            }

            self.save_output("extraction_node", doc_type, test_data)

        except Exception as e:
            error_data = {
                "component": "extraction_node",
                "document_type": doc_type,
                "error": str(e),
                "success": False
            }
            self.save_output("extraction_node", f"{doc_type}_error", error_data)

    async def run_all_tests(self, setup_data: bool = True) -> None:
        """Run all component tests."""
        self.logger.info("Starting comprehensive component testing...")

        try:
            # Setup test data if requested
            if setup_data:
                await self.setup_test_data()

            # Test services
            await self.test_classification_service()
            await self.test_preference_manager()
            await self.test_feedback_context_manager()

            # Test nodes
            await self.test_nodes()

            # Generate summary report
            self.generate_summary_report()

            self.logger.info("All component tests completed!")

            # Cleanup test data if it was setup
            if setup_data:
                await self.cleanup_test_data()

        except Exception as e:
            self.logger.error(f"Test suite failed: {e}")
            raise

    def generate_summary_report(self) -> None:
        """Generate summary report of all tests."""
        output_files = [f for f in os.listdir(self.output_dir) if f.endswith('.json')]

        summary = {
            "test_run": datetime.now().isoformat(),
            "total_tests": len(output_files),
            "components_tested": [],
            "success_count": 0,
            "failure_count": 0,
            "files_generated": output_files
        }

        components = set()

        for filename in output_files:
            try:
                with open(os.path.join(self.output_dir, filename), 'r') as f:
                    data = json.load(f)
                    component = data.get("component", "unknown")
                    components.add(component)

                    if data.get("success", False):
                        summary["success_count"] += 1
                    else:
                        summary["failure_count"] += 1

            except Exception as e:
                self.logger.warning(f"Could not read {filename}: {e}")

        summary["components_tested"] = sorted(list(components))

        # Save summary
        summary_file = os.path.join(self.output_dir, f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Test summary saved to {summary_file}")
        print(f"\nTest Summary:")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['success_count']}")
        print(f"Failed: {summary['failure_count']}")
        print(f"Components: {', '.join(summary['components_tested'])}")


async def main():
    """Run the component use case tester."""
    logging.basicConfig(level=logging.INFO)

    tester = ComponentUseCaseTester()

    # Run tests with database setup (default)
    print("Running comprehensive component tests with database setup...")
    await tester.run_all_tests(setup_data=True)

    print("\nAlternatively, you can:")
    print("1. Run without DB setup: await tester.run_all_tests(setup_data=False)")
    print("2. Setup data only: await tester.setup_test_data()")
    print("3. Run individual tests: await tester.test_classification_service()")
    print(f"4. Check outputs in: {tester.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
