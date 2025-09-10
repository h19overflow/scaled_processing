"""
Document classification agent for structured extraction.
Detects document types using LLM and keyword fallback.
"""
import logging
import os
from typing import Dict
from uuid import UUID, uuid4

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from ..models.schema import DocumentClassificationResult
from dotenv import load_dotenv
load_dotenv()


class DocumentClassificationDeps(BaseModel):
    """Dependencies for document classification agent."""
    document_text: str
    text_sample: str


# Create the pydantic AI agent
classification_agent = Agent(
    'gemini-2.0-flash',
    result_type=DocumentClassificationResult,
    deps_type=DocumentClassificationDeps,
)


@classification_agent.system_prompt
def classification_system_prompt(ctx: RunContext[DocumentClassificationDeps]) -> str:
    """Create classification instructions for the AI agent."""
    return f"""You are an expert document classifier. Analyze the provided document and classify it into one of these categories:

- **contract**: Legal agreements, terms of service, employment contracts, service agreements
- **invoice**: Bills, invoices, payment requests, receipts, financial documents
- **resume**: CVs, resumes, job applications, employment documents, professional profiles  
- **legal**: Court documents, legal filings, law documents, legal notices
- **medical**: Medical records, prescriptions, health documents, patient information
- **attendance**: Time tracking, attendance records, work schedules, timesheets
- **report**: Business reports, analysis documents, monthly reports, performance reports
- **other**: Any document that doesn't fit the above categories

IMPORTANT: The document text below is formatted in three sections to give you comprehensive coverage of the document:
- [DOCUMENT BEGINNING]: First ~1000 characters from the start
- [DOCUMENT MIDDLE]: ~1000 characters from the middle section  
- [DOCUMENT END]: Last ~1000 characters from the end

This format ensures you see the document's structure from beginning to end, including headers, content, and conclusions.

Document text to classify:
{ctx.deps.text_sample}

Provide:
1. The most appropriate classification
2. A confidence score (0.0-1.0) based on how certain you are
3. Brief reasoning for your decision (consider patterns from all three sections)
4. Key terms/phrases that influenced your classification
"""


class ClassificationAgent:
    """The main classification agent for document type detection."""
    
    def __init__(self):
        """Initialize the classification agent."""
        self.logger = logging.getLogger(__name__)
    
    async def classify_document(self, document_text: str) -> Dict[str, any]:
        """Classify document using the LLM agent."""
        try:
            self.logger.info(f"Starting document classification for text of length: {len(document_text)}")
            
            # Create comprehensive text sample from beginning, middle, and end
            text_sample = self._create_comprehensive_sample(document_text)
            self.logger.info(f"Created text sample of length: {len(text_sample)}")
            
            # Create dependencies
            deps = DocumentClassificationDeps(
                document_text=document_text,
                text_sample=text_sample
            )
            
            self.logger.info("Running classification agent...")
            
            # Run the classification agent
            result = await classification_agent.run(
                "Please classify this document according to the categories and requirements provided.",
                deps=deps
            )
            
            self.logger.info(f"Agent completed. Raw result type: {type(result)}")
            self.logger.info(f"Result data type: {type(result.data)}")
            
            # Convert structured result to dictionary
            classification_result = result.data
            final_result = {
                "classification": classification_result.classification,
                "confidence": classification_result.confidence,
                "reasoning": classification_result.reasoning,
                "keywords": classification_result.keywords_found
            }
            
            self.logger.info(f"Classification complete: {classification_result.classification} (confidence: {classification_result.confidence})")
            return final_result

        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"classification": "other", "confidence": 0.0, "keywords": []}

    # HELPER FUNCTIONS
    def _create_comprehensive_sample(self, document_text: str, sample_size: int = 3000) -> str:
        """Create a comprehensive text sample from beginning, middle, and end of document."""
        if len(document_text) <= sample_size:
            return document_text
        
        # Calculate section sizes
        section_size = sample_size // 3
        total_length = len(document_text)
        
        # Extract sections
        beginning = document_text[:section_size]
        middle_start = (total_length - section_size) // 2
        middle = document_text[middle_start:middle_start + section_size]
        end = document_text[-section_size:]
        
        # Create formatted sample with clear section indicators
        comprehensive_sample = f"""[DOCUMENT BEGINNING - First {section_size} characters]
{beginning}

[DOCUMENT MIDDLE - {section_size} characters from middle section]  
{middle}

[DOCUMENT END - Last {section_size} characters]
{end}"""
        
        return comprehensive_sample