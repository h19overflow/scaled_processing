"""
Enhanced structured extraction demo showcasing feedback, preferences, and classification.
"""

import asyncio
import logging
from typing import Dict, Any
from uuid import uuid4

from .graph import build_graph, create_initial_state
from ..config.settings import Settings
from ..services.classification_service import DocumentClassificationService
from ..services.feedback_context_manager import FeedbackContextManager
from ..services.preference_manager import PreferenceManager
from ...core_deps.database.connection_manager import ConnectionManager

# Sample documents for testing
SAMPLE_DOCUMENTS = {
    "contract": """
    EMPLOYMENT AGREEMENT
    
    This Employment Agreement is made between TechCorp Inc. and John Doe.
    
    TERMS OF EMPLOYMENT:
    1. Position: Senior Software Engineer
    2. Start Date: January 1, 2024
    3. Salary: $120,000 per year
    4. Benefits: Health insurance, 401k, vacation days
    5. Termination: 30 days notice required
    
    The employee agrees to maintain confidentiality and non-compete clauses.
    """,

    "invoice": """
    INVOICE #INV-2024-001
    
    Bill To: Acme Corporation
    123 Business St
    City, State 12345
    
    Invoice Date: March 15, 2024
    Due Date: April 15, 2024
    
    ITEMS:
    - Web Development Services: $5,000.00
    - Hosting Setup: $500.00  
    - Domain Registration: $15.00
    
    Subtotal: $5,515.00
    Tax (8.5%): $468.78
    Total Amount Due: $5,983.78
    
    Payment Terms: Net 30 days
    """,

    "resume": """
    JOHN DOE
    Software Engineer
    john.doe@email.com | (555) 123-4567
    
    EXPERIENCE:
    Senior Developer at TechCorp (2020-2024)
    - Led team of 5 developers on microservices architecture
    - Improved system performance by 40%
    - Technologies: Python, React, PostgreSQL
    
    Junior Developer at StartupCo (2018-2020)
    - Built REST APIs and frontend components
    - Worked with agile methodology
    
    EDUCATION:
    B.S. Computer Science, University of Technology (2018)
    
    SKILLS:
    Python, JavaScript, React, PostgreSQL, Docker, AWS
    """
}


class EnhancedExtractionDemo:
    """Demo class showcasing enhanced extraction features."""

    def __init__(self):
        """Initialize demo with required services."""
        self.logger = logging.getLogger(__name__)
        self.connection_manager = ConnectionManager()
        self.settings = Settings()

        # Initialize services
        self.classification_service = DocumentClassificationService(self.connection_manager)
        self.feedback_manager = FeedbackContextManager(self.connection_manager)
        self.preference_manager = PreferenceManager(self.connection_manager)

    async def run_demo(self, user_id: str = "demo_user"):
        """Run complete demo showcasing all enhancement features."""
        print(">>> Enhanced Structured Extraction Demo")
        print("=" * 50)

        # Step 1: Setup user preferences for each document type
        print("\n[1] Setting up user preferences...")
        await self._setup_demo_preferences(user_id)

        # Step 2: Run extraction on sample documents
        for doc_type, document_text in SAMPLE_DOCUMENTS.items():
            print(f"\n[2] Processing {doc_type.upper()} document...")

            # Generate document ID
            document_id = str(uuid4())

            # Run enhanced extraction workflow
            result = await self._run_enhanced_extraction(
                document_text=document_text,
                document_id=document_id,
                user_id=user_id
            )

            # Display results
            self._display_results(doc_type, result)

            # Simulate user feedback
            print(f"\n💬 Capturing user feedback for {doc_type}...")
            await self._capture_demo_feedback(document_id, user_id, doc_type, result)

    async def _setup_demo_preferences(self, user_id: str):
        """Setup demo preferences for different document types."""
        preferences_config = {
            "contract": {
                "field_preferences": {
                    "field_priorities": {
                        "party_names": {"weight": 1.0, "required": True},
                        "salary": {"weight": 0.9, "required": True},
                        "start_date": {"weight": 0.8, "required": True},
                        "position": {"weight": 0.7, "required": True}
                    },
                    "extraction_rules": {
                        "dates_format": "YYYY-MM-DD",
                        "currency_format": "USD"
                    }
                },
                "extraction_style": {
                    "verbosity": "detailed",
                    "format_preference": "structured",
                    "confidence_threshold": 0.8
                },
                "prompt_instructions": "Focus on legal terms and financial details"
            },

            "invoice": {
                "field_preferences": {
                    "field_priorities": {
                        "total_amount": {"weight": 1.0, "required": True},
                        "due_date": {"weight": 0.9, "required": True},
                        "invoice_number": {"weight": 0.8, "required": False}
                    }
                },
                "extraction_style": {
                    "verbosity": "standard",
                    "confidence_threshold": 0.7,
                    "output_formatting": {
                        "numbers": "with_separators",
                        "dates": "ISO_8601"
                    }
                },
                "prompt_instructions": "Extract all monetary values and payment terms"
            },

            "resume": {
                "field_preferences": {
                    "field_priorities": {
                        "experience": {"weight": 1.0, "required": True},
                        "skills": {"weight": 0.9, "required": True},
                        "education": {"weight": 0.7, "required": False}
                    }
                },
                "extraction_style": {
                    "verbosity": "comprehensive",
                    "context_awareness": True,
                    "cross_reference": True
                },
                "prompt_instructions": "Focus on technical skills and work experience"
            }
        }

        for doc_type, prefs in preferences_config.items():
            success = await self.preference_manager.save_user_preferences(
                user_id=user_id,
                classification=doc_type,
                field_preferences=prefs["field_preferences"],
                extraction_style=prefs["extraction_style"],
                prompt_instructions=prefs["prompt_instructions"]
            )
            print(f"  [OK] {doc_type} preferences: {'saved' if success else 'failed'}")

    async def _run_enhanced_extraction(
            self,
            document_text: str,
            document_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Run the enhanced extraction workflow."""
        try:
            # Create initial state
            initial_state = create_initial_state(
                document_text=document_text,
                document_id=document_id,
                user_id=user_id
            )

            # Build and run graph
            graph = build_graph(self.settings)
            result = await graph.ainvoke(initial_state)

            return result

        except Exception as e:
            self.logger.error(f"Enhanced extraction failed: {e}")
            return {"error": str(e)}

    def _display_results(self, doc_type: str, result: Dict[str, Any]):
        """Display extraction results with enhancement details."""
        print(f"\n[RESULTS] for {doc_type.upper()}:")

        # Classification results
        classification = result.get("classification", "unknown")
        confidence = result.get("classification_confidence", 0.0)
        print(f"  🔍 Classification: {classification} (confidence: {confidence:.2f})")

        # Feedback context
        feedback_context = result.get("feedback_context", {})
        feedback_items = len(feedback_context.get("relevant_feedback", []))
        print(f"  💭 Feedback context: {feedback_items} relevant items")

        # User preferences
        preferences = result.get("user_preferences", {})
        has_custom_instructions = bool(preferences.get("prompt_instructions"))
        print(f"  ⚙️ User preferences: {'custom' if has_custom_instructions else 'default'}")

        # Extraction status
        status = result.get("status", "unknown")
        print(f"  ✨ Status: {status}")

        # Show any errors
        error = result.get("error")
        if error:
            print(f"  [ERROR] Error: {error}")

    async def _capture_demo_feedback(
            self,
            document_id: str,
            user_id: str,
            doc_type: str,
            result: Dict[str, Any]
    ):
        """Capture simulated user feedback."""
        # Simulate positive feedback with field-specific corrections
        feedback_data = {
            "classification": doc_type,
            "type": "field_correction",
            "rating": 4,
            "comment": f"Good extraction for {doc_type}, minor formatting improvements needed",
            "fields": {
                "total_amount": {"correction": "Always include currency symbol"},
                "dates": {"correction": "Use MM/DD/YYYY format for US documents"}
            }
        }

        success = await self.feedback_manager.capture_feedback(
            document_id=document_id,
            user_id=user_id,
            feedback_data=feedback_data
        )

        print(f"  [{'OK' if success else 'ERROR'}] Feedback captured: {feedback_data['comment']}")


async def main():
    """Main demo runner."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Run demo
    demo = EnhancedExtractionDemo()
    await demo.run_demo(user_id="demo_user_123")

    print("\n🎉 Enhanced extraction demo completed!")
    print("Features demonstrated:")
    print("  [OK] Document classification with LLM + keyword fallback")
    print("  [OK] User preference loading and application")
    print("  [OK] Feedback context integration")
    print("  [OK] Enhanced workflow with 3 new pipeline steps")
    print("  [OK] Field-level feedback capture")


if __name__ == "__main__":
    asyncio.run(main())
