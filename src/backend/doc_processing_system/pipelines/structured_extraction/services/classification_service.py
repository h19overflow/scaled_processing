"""
Document classification service for structured extraction.
Detects document types using LLM and keyword fallback.
"""
import logging
import os
from typing import Dict, List, Optional

import google.generativeai as genai

from src.backend.doc_processing_system.core_deps.database.CRUD.classification_crud import ClassificationCRUD
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager


class DocumentClassificationService:
    """Core logic for document classification."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize classification service."""
        self.connection_manager = connection_manager
        self.classification_crud = ClassificationCRUD(connection_manager)
        self.logger = logging.getLogger(__name__)

        # Initialize Gemini client
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def classify_document(
            self,
            document_text: str,
            document_id: str,
            user_id: str
    ) -> Dict[str, any]:
        """Classify document using LLM with keyword fallback."""
        try:
            # Try LLM classification first
            llm_result = await self._classify_with_llm(document_text)

            if llm_result["confidence"] >= 0.7:
                classification_result = llm_result
                classification_result["method"] = "llm"
            else:
                # Fall back to keyword-based classification
                keyword_result = self._classify_with_keywords(document_text)
                classification_result = keyword_result
                classification_result["method"] = "keyword"

            # Store classification in database
            self.classification_crud.create_classification(
                document_id=document_id,
                user_id=user_id,
                classification=classification_result["classification"],
                confidence_score=classification_result["confidence"],
                classification_method=classification_result["method"],
                keywords_found=classification_result.get("keywords", [])
            )

            return classification_result

        except Exception as e:
            self.logger.error(f"Classification failed: {e}")
            # Return default classification
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "method": "fallback",
                "keywords": []
            }

    async def _classify_with_llm(self, document_text: str) -> Dict[str, any]:
        """Classify document using LLM."""
        try:
            # Truncate text to avoid token limits
            text_sample = document_text[:3000] if len(document_text) > 3000 else document_text

            prompt = f"""
            Classify this document into one of these categories:
            - contract: Legal agreements, terms of service, contracts
            - invoice: Bills, invoices, payment requests, receipts
            - resume: CVs, resumes, job applications, employment documents
            - legal: Court documents, legal filings, law documents
            - medical: Medical records, prescriptions, health documents
            - other: Any other document type
            
            Document text:
            {text_sample}
            
            Respond with only the category name and confidence (0.0-1.0):
            Format: "category,confidence"
            """

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=50,
                    temperature=0.1,
                )
            )

            result = response.text.strip()
            parts = result.split(",")

            if len(parts) == 2:
                classification = parts[0].strip().lower()
                confidence = float(parts[1].strip())

                return {
                    "classification": classification,
                    "confidence": confidence
                }
            else:
                raise ValueError("Invalid LLM response format")

        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            return {"classification": "unknown", "confidence": 0.0}

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
            "medical": ["patient", "diagnosis", "treatment", "medical", "symptoms", "doctor", "prescription", "health"]
        }

    def get_document_classification(self, document_id: str) -> Optional[Dict[str, any]]:
        """Get existing classification for document."""
        try:
            classification = self.classification_crud.get_document_classification(document_id)

            if classification:
                return {
                    "classification": classification.classification,
                    "confidence": classification.confidence_score,
                    "method": classification.classification_method,
                    "keywords": classification.keywords_found
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get classification: {e}")
            return None
