"""
Document classification service for structured extraction.
Detects document types using LLM and keyword fallback.
"""
import logging
from typing import Dict, List, Optional

from ..agents.classification_agent import ClassificationAgent
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager


class DocumentClassificationService:
    """Core logic for document classification."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize classification service."""
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        self.classification_agent = ClassificationAgent()
    async def classify_document(self, document_text: str) -> Dict[str, any]:
        """Classify document using LLM with keyword fallback."""
        try:
            self.logger.info("=== CLASSIFICATION SERVICE STARTING ===")
            self.logger.info(f"Document text length: {len(document_text)}")
            
            # Try LLM classification first
            self.logger.info("Attempting LLM classification...")
            llm_result = await self.classification_agent.classify_document(document_text)
            
            self.logger.info(f"LLM classification result: {llm_result}")
            self.logger.info(f"LLM confidence: {llm_result.get('confidence', 0.0)}")

            if llm_result["confidence"] >= 0.7:
                self.logger.info("Using LLM result (confidence >= 0.7)")
                classification_result = llm_result
                classification_result["method"] = "llm"
            else:
                # Fall back to keyword-based classification
                self.logger.info(f"LLM confidence too low ({llm_result['confidence']}), falling back to keywords...")
                keyword_result = self._classify_with_keywords(document_text)
                self.logger.info(f"Keyword classification result: {keyword_result}")
                classification_result = keyword_result
                classification_result["method"] = "keyword"

            self.logger.info(f"Final classification: {classification_result}")
            self.logger.info("=== CLASSIFICATION SERVICE COMPLETE ===")
            return classification_result

        except Exception as e:
            self.logger.error(f"Classification failed: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            # Return default classification
            return {
                "classification": "other",
                "confidence": 0.0,
                "method": "fallback",
                "keywords": []
            }


    def _classify_with_keywords(self, document_text: str) -> Dict[str, any]:
        """Classify document using keyword matching."""
        keywords_map = self.get_classification_keywords()
        text_lower = document_text.lower()

        scores = {}
        found_keywords = {}

        for doc_type, keywords in keywords_map.items():
            score = 0
            type_keywords = []

            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
                    type_keywords.append(keyword)

            if score > 0:
                scores[doc_type] = score / len(keywords)  # Normalize by total keywords
                found_keywords[doc_type] = type_keywords

        if not scores:
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "keywords": []
            }

        # Get best match
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] * 2, 1.0)  # Scale to confidence

        return {
            "classification": best_type,
            "confidence": confidence,
            "keywords": found_keywords[best_type]
        }

    def get_classification_keywords(self) -> Dict[str, List[str]]:
        """Get keyword mappings for rule-based classification."""
        return {
            "contract": ["agreement", "contract", "parties", "terms", "obligations", "whereas", "party", "shall"],
            "invoice": ["invoice", "bill", "payment", "due", "amount", "vendor", "total", "tax", "remit"],
            "resume": ["experience", "education", "skills", "employment", "cv", "objective", "work", "university"],
            "legal": ["whereas", "plaintiff", "defendant", "court", "jurisdiction", "legal", "attorney", "counsel"],
            "medical": ["patient", "diagnosis", "treatment", "medical", "symptoms", "doctor", "prescription", "health"],
            "attendance": ["attendance", "time in", "time out", "hours", "date", "work from home", "wfh", "timesheet"],
            "report": ["report", "analysis", "summary", "findings", "monthly", "quarterly", "performance", "status"]
        }

    # HELPER FUNCTIONS

    def get_user_classification_keywords(self, user_id: str) -> Dict[str, List[str]]:
        """Get user's custom classification keywords from database or use defaults."""
        try:
            # TODO: Implement database lookup for user's custom keywords
            # For now, return default keywords
            return self.get_classification_keywords()
        except Exception as e:
            self.logger.error(f"Failed to get user classification keywords: {e}")
            return self.get_classification_keywords()
