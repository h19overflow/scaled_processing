Enhanced Structured Extraction - Core Logic Proof of Concept │ │
│ │ │ │
│ │ Overview │ │
│ │ │ │
│ │ Implement feedback capture, user preferences, and document classification as core logic components integrated
directly into the structured extraction pipeline, without │ │
│ │ Kafka producers for now. │ │
│ │ │ │
│ │ Phase 1: Database Schema Extensions (Day 1)
│ │
│ │ │ │
│ │ 1.1 Add New Tables to models.py │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/core_deps/database/models.py │ │
│ │ │ │
│ │ New Models to Add:
│ │
│ │ # DocumentFeedbackModel - User feedback on extraction results │ │
│ │ class DocumentFeedbackModel(Base):
│ │
│ │     __tablename__ = "document_feedback"
│ │
│ │ │ │
│ │ id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
│ │
│ │ document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
│ │
│ │ classification = Column(String(100), nullable=False, index=True)  # contract, invoice, resume, etc. │ │
│ │ feedback_type = Column(String(50), nullable=False)  # positive, negative, correction, field_missing, field_wrong │ │
│ │ feedback_rating = Column(Integer)  # 1-5 star rating │ │
│ │ user_id = Column(String(255), nullable=False, index=True)
│ │
│ │ feedback_comment = Column(Text)  # Free-form feedback │ │
│ │ extraction_fields = Column(JSON)  # Per-field feedback: {"field_name": {"status": "correct|wrong|missing", "
correction": "value", "comment": "text"}} │ │
│ │ system_generated = Column(Boolean, default=False)
│ │
│ │ created_at = Column(DateTime(timezone=True), default=func.now())
│ │
│ │ │ │
│ │ # UserPreferencesModel - User extraction preferences per document type │ │
│ │ class UserPreferencesModel(Base):
│ │
│ │     __tablename__ = "user_preferences"
│ │
│ │ │ │
│ │ id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
│ │
│ │ user_id = Column(String(255), nullable=False, index=True)
│ │
│ │ classification = Column(String(100), nullable=False, index=True)  # document type │ │
│ │ field_preferences = Column(JSON)  # Detailed field preferences (see spec below)
│ │
│ │ extraction_style = Column(JSON)  # Style preferences (see spec below)
│ │
│ │ prompt_instructions = Column(Text)  # Custom extraction instructions │ │
│ │ created_at = Column(DateTime(timezone=True), default=func.now())
│ │
│ │ updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
│ │
│ │ │ │
│ │ # DocumentClassificationModel - Document type classifications │ │
│ │ class DocumentClassificationModel(Base):
│ │
│ │     __tablename__ = "document_classifications"
│ │
│ │ │ │
│ │ id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
│ │
│ │ document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
│ │
│ │ classification = Column(String(100), nullable=False, index=True)
│ │
│ │ confidence_score = Column(Float, nullable=False)
│ │
│ │ classification_method = Column(String(50), nullable=False)  # llm, rule_based, manual │ │
│ │ keywords_found = Column(ARRAY(String))  # Keywords that influenced classification │ │
│ │ user_id = Column(String(255), nullable=False, index=True)
│ │
│ │ created_at = Column(DateTime(timezone=True), default=func.now())
│ │
│ │ │ │
│ │ 1.2 Preference Specifications │ │
│ │ │ │
│ │ Field Preferences JSON Structure:
│ │
│ │ { │ │
│ │   "field_priorities": { │ │
│ │     "company_name": {"weight": 1.0, "required": true, "extraction_style": "exact"}, │ │
│ │     "payment_terms": {"weight": 0.9, "required": true, "extraction_style": "detailed"}, │ │
│ │     "contract_dates": {"weight": 0.8, "required": false, "extraction_style": "normalized"}, │ │
│ │     "parties_involved": {"weight": 0.7, "required": true, "extraction_style": "structured"} │ │
│ │ }, │ │
│ │   "field_mappings": { │ │
│ │     "vendor": "company_name", // Map alternate field names │ │
│ │     "supplier": "company_name"
│ │
│ │ }, │ │
│ │   "extraction_rules": { │ │
│ │     "dates_format": "YYYY-MM-DD", │ │
│ │     "currency_format": "USD", │ │
│ │     "name_format": "full_legal_name"
│ │
│ │ } │ │
│ │ } │ │
│ │ │ │
│ │ Extraction Style JSON Structure:
│ │
│ │ { │ │
│ │   "verbosity": "detailed", // minimal, standard, detailed, comprehensive │ │
│ │   "format_preference": "structured", // raw_text, structured, key_value_pairs │ │
│ │   "language": "en", │ │
│ │   "confidence_threshold": 0.7, // Min confidence for field extraction │ │
│ │   "context_awareness": true, // Use document context for extraction │ │
│ │   "cross_reference": true, // Cross-reference fields for consistency │ │
│ │   "fallback_behavior": "skip", // skip, approximate, flag_for_review │ │
│ │   "output_formatting": { │ │
│ │     "dates": "ISO_8601", │ │
│ │     "numbers": "with_separators", │ │
│ │     "addresses": "single_line", │ │
│ │     "phone_numbers": "international_format"
│ │
│ │ } │ │
│ │ } │ │
│ │ │ │
│ │ 1.3 Create CRUD Operations │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/core_deps/database/CRUD/ │ │
│ │ │ │
│ │ New Files:
│ │
│ │ - feedback_crud.py - CRUD for document feedback │ │
│ │ - preferences_crud.py - CRUD for user preferences │ │
│ │ - classification_crud.py - CRUD for document classifications │ │
│ │ │ │
│ │ Phase 2: Core Service Components (Day 2-3)
│ │
│ │ │ │
│ │ 2.1 Document Classification Service │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/messaging/extraction_pipeline/ │ │
│ │ │ │
│ │ New File: classification_service.py │ │
│ │ class DocumentClassificationService:
│ │
│ │     """Core logic for document classification."""
│ │
│ │ │ │
│ │ async def classify_document(self, document_text: str, document_id: str, user_id: str) -> Dict:
│ │
│ │ # 1. LLM-based classification using document content │ │
│ │ # 2. Rule-based fallback using keyword matching │ │
│ │ # 3. Store classification result in database │ │
│ │ return { │ │
│ │             "classification": "contract", │ │
│ │             "confidence": 0.89, │ │
│ │             "method": "llm", │ │
│ │             "keywords": ["agreement", "parties", "terms"]
│ │
│ │ } │ │
│ │ │ │
│ │ def get_classification_keywords(self) -> Dict[str, List[str]]:
│ │
│ │ # Keyword mappings for rule-based classification │ │
│ │ return { │ │
│ │             "contract": ["agreement", "contract", "parties", "terms", "obligations"], │ │
│ │             "invoice": ["invoice", "bill", "payment", "due", "amount", "vendor"], │ │
│ │             "resume": ["experience", "education", "skills", "employment", "cv"], │ │
│ │             "legal": ["whereas", "plaintiff", "defendant", "court", "jurisdiction"], │ │
│ │             "medical": ["patient", "diagnosis", "treatment", "medical", "symptoms"]
│ │
│ │ } │ │
│ │ │ │
│ │ 2.2 Feedback Context Manager │ │
│ │ │ │
│ │ New File: feedback_context_manager.py │ │
│ │ class FeedbackContextManager:
│ │
│ │     """Core logic for managing feedback context in extractions."""
│ │
│ │ │ │
│ │ async def get_feedback_context(self, classification: str, user_id: str) -> Dict:
│ │
│ │ # 1. Load user preferences for document type │ │
│ │ # 2. Get top-rated feedback for this classification │ │
│ │ # 3. Build context prompt incorporating both │ │
│ │ return { │ │
│ │             "user_preferences": {...}, │ │
│ │             "relevant_feedback": [...], │ │
│ │             "context_prompt": "Based on previous feedback, focus on...", │ │
│ │             "field_priorities": {...} │ │
│ │ } │ │
│ │ │ │
│ │ def build_enhancement_prompt(self, feedback_data: List[Dict], preferences: Dict) -> str:
│ │
│ │ # Generate prompt section to inject into agent prompts │ │
│ │ # Include user corrections, field priorities, style preferences │ │
│ │ │ │
│ │ async def capture_feedback(self, document_id: str, user_id: str, feedback_data: Dict):
│ │
│ │ # Store feedback with field-level details │ │
│ │ # Update context ranking for future extractions │ │
│ │ │ │
│ │ 2.3 Preference Manager │ │
│ │ │ │
│ │ New File: preference_manager.py │ │
│ │ class PreferenceManager:
│ │
│ │     """Core logic for user preference management."""
│ │
│ │ │ │
│ │ async def get_user_preferences(self, user_id: str, classification: str) -> Dict:
│ │
│ │ # Load user preferences for specific document type │ │
│ │ # Return default preferences if none exist │ │
│ │ │ │
│ │ async def apply_preferences_to_schema(self, schema: Dict, preferences: Dict) -> Dict:
│ │
│ │ # Modify extraction schema based on user preferences │ │
│ │ # Adjust field weights, requirements, extraction styles │ │
│ │ │ │
│ │ def generate_preference_prompt_injection(self, preferences: Dict) -> str:
│ │
│ │ # Generate prompt text to inject user preferences into agent prompts │ │
│ │ # Include field priorities, style preferences, custom instructions │ │
│ │ │ │
│ │ Phase 3: Enhanced Pipeline Integration (Day 3-4)
│ │
│ │ │ │
│ │ 3.1 Enhanced State Model │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/pipelines/structured_extraction/models/state.py │ │
│ │ │ │
│ │ Add to MultiAgentState:
│ │
│ │ classification: Optional[str]
│ │
│ │ classification_confidence: Optional[float]
│ │
│ │ user_id: Optional[str]
│ │
│ │ feedback_context: Optional[Dict[str, Any]]
│ │
│ │ user_preferences: Optional[Dict[str, Any]]
│ │
│ │ enhancement_prompt: Optional[str]
│ │
│ │ │ │
│ │ 3.2 New Pipeline Nodes │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/pipelines/structured_extraction/nodes/ │ │
│ │ │ │
│ │ New Files:
│ │
│ │ - classification.py - Document classification node │ │
│ │ - context_loading.py - Feedback context loading node │ │
│ │ - preference_injection.py - User preference injection node │ │
│ │ │ │
│ │ 3.3 Enhanced Discovery Node │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/pipelines/structured_extraction/nodes/discovery.py │ │
│ │ │ │
│ │ Enhancements:
│ │
│ │ - Inject feedback context into agent prompts │ │
│ │ - Apply user field preferences to discovery process │ │
│ │ - Use classification-specific discovery strategies │ │
│ │ │ │
│ │ 3.4 Enhanced Graph Orchestrator │ │
│ │ │ │
│ │ Target: src/backend/doc_processing_system/pipelines/structured_extraction/graph.py │ │
│ │ │ │
│ │ New Workflow:
│ │
│ │ 1. classify_document → Determine document type and confidence │ │
│ │ 2. load_feedback_context → Get relevant feedback and user preferences │ │
│ │ 3. inject_preferences → Apply preferences to extraction strategy │ │
│ │ 4. chunk_document → Use existing chunking (unchanged)
│ │
│ │ 5. enhanced_sequential_discovery → Context-aware discovery │ │
│ │ 6. consolidate_schema → Preference-aware consolidation │ │
│ │ 7. generate_config → Use existing config generation │ │
│ │ 8. extract_data → Use existing extraction │ │
│ │ 9. prepare_feedback_request → Prepare results for feedback collection │ │
│ │ │ │
│ │ Phase 4: Demo & Testing (Day 4-5)
│ │
│ │ │ │
│ │ 4.1 Test Data Setup │ │
│ │ │ │
│ │ Mock Data Creation:
│ │
│ │ - User preferences for different document types │ │
│ │ - Historical feedback examples with corrections │ │
│ │ - Sample documents: contract, invoice, resume │ │
│ │ │ │
│ │ 4.2 Demo Script │ │
│ │ │ │
│ │ File: demo_enhanced_extraction.py │ │
│ │ async def demo_enhanced_extraction():
│ │
│ │ # Setup: Create user with preferences │ │
│ │ # Setup: Add mock feedback history │ │
│ │ # Test 1: Extract from contract with preferences │ │
│ │ # Test 2: Show field priority differences │ │
│ │ # Test 3: Apply feedback corrections │ │
│ │ # Test 4: Re-extract showing improvement │ │
│ │ # Output: Before/after comparison reports │ │
│ │ │ │
│ │ 4.3 Integration Testing │ │
│ │ │ │
│ │ Test Scenarios:
│ │
│ │ 1. New User, New Document Type: Default behavior │ │
│ │ 2. Existing User, Preferred Document Type: Apply preferences │ │
│ │ 3. Document with Previous Feedback: Use feedback context │ │
│ │ 4. Complex Preferences: Field priorities + style settings │ │
│ │ 5. Feedback Loop: Extract → Feedback → Re-extract │ │
│ │ │ │
│ │ Expected Deliverables │ │
│ │ │ │
│ │ - ✅ Enhanced database schema with 3 new tables │ │
│ │ - ✅ Core classification service (no external calls)
│ │
│ │ - ✅ Feedback context management system │ │
│ │ - ✅ Preference application in extraction pipeline │ │
│ │ - ✅ Enhanced structured extraction workflow │ │
│ │ - ✅ Demo showcasing all features with test documents │ │
│ │ │ │
│ │ Success Criteria │ │
│ │ │ │
│ │ 1. Document Classification: Accurate type detection for test docs │ │
│ │ 2. Preference Application: User preferences visibly affect extraction │ │
│ │ 3. Feedback Integration: Previous feedback influences new extractions │ │
│ │ 4. End-to-End Flow: Complete classify→apply_preferences→extract→feedback cycle │ │
│ │ 5. Database Integration: All data properly stored and retrieved │ │
│ │ │ │
│ │ This approach builds the core feedback and personalization logic directly into the extraction pipeline without
external messaging complexity.       