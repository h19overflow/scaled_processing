
### Guiding Principles for This Plan

1.  **Build the "Steel Thread" First:** We'll start by creating the simplest possible end-to-end path for a message to travel through the system. This proves the core plumbing works.
2.  **Layer Complexity Incrementally:** We'll start with the simplest RAG pipeline because it's more linear. Then, we'll build the more complex, parallel Structured Extraction pipeline on top of that solid foundation.
3.  **Test at Every Stage:** Each sprint's "Definition of Done" includes specific testing requirements. This is non-negotiable for building a robust system.

---

### Sprint 0: The Foundation - Setup and Configuration

**Goal:** Prepare the development environment and create the foundational, non-functional components. You can't build the house without laying the foundation and having your tools ready.

**Components to Build:**
*   **Project Structure:** Create the directory layout (`src/backend/api`, `core_services`, `messaging`, etc.).
*   **Configuration (`config` Layer):** Implement the `Settings` singleton class to load configuration from environment variables (.env file).
*   **Docker Compose:** Create a `docker-compose.yml` file to manage all your services: Kafka, Zookeeper, PostgreSQL, and ChromaDB. This is **critical** for a clean development environment.
*   **Core Data Models (`models` Layer):** Define the basic Pydantic/dataclass models: `IDocument`, `Document`, `IChunk`, `Chunk`. Don't worry about all the methods yet, just the data attributes.

**Implementation Steps:**
1.  Set up a virtual environment and `requirements.txt`.
2.  Write the `Settings` class to load API keys, DSNs, etc.
3.  Write the `docker-compose.yml` file. Get all the services running (`docker-compose up`).
4.  Define the core data structures.

**✅ Definition of Done:**
*   The project structure is created.
*   The `Settings` class can successfully load configuration.
*   `docker-compose up` starts Kafka, Postgres, and Chroma without errors.
*   The core data models are defined.

---

### Sprint 1: The Core Messaging Pipeline (The Steel Thread)

**Goal:** Get a message from the API to a consumer through Kafka. This is the most important first step to validate your event-driven architecture.

**Components to Build:**
*   **Document Ingestion API (`infra` Layer):** A very basic FastAPI endpoint (`/upload`) that accepts a file, logs its name, and does nothing else yet.
*   **Kafka Producer (`messaging` Layer):** A simple producer that implements `IEventPublisher`. It will have one method: `send_document_received(document_name: str)`.
*   **Kafka Consumer (`messaging` Layer):** A basic consumer that subscribes to the `document-received` topic and simply logs the messages it receives.

**Implementation Steps:**
1.  Create the FastAPI app and the `/upload` endpoint.
2.  Integrate the `KafkaProducer` into the endpoint. When a file is uploaded, call the producer to send a message.
3.  Write the standalone `KafkaConsumer` script. It should connect to Kafka and listen for messages.

**✅ Definition of Done:**
*   **Integration Test:** When you send a file to the `/upload` endpoint, the filename is **instantly printed in the logs of your separate Kafka consumer script.**
*   Unit tests for the producer (mocking the Kafka client) are written.
*   The `document-received` Kafka topic is created and used.

---

### Sprint 2: Basic Document Persistence

**Goal:** Persist the metadata of the uploaded document into the PostgreSQL database. This connects your pipeline to your first data store.

**Components to Build:**
*   **Persistence Manager (`core` Layer):** Implement the `PersistenceManager` and the `IPersistenceRepository` interface.
*   **PostgreSQL Repository:** Create a concrete implementation of `IPersistenceRepository` for your `Document` model that can save data to PostgreSQL.
*   **Update the Consumer:** Modify the consumer from Sprint 1. When it receives a `document-received` event, it should now use the `PersistenceManager` to save a `Document` record to the database.

**Implementation Steps:**
1.  Set up your database connection logic (e.g., using SQLAlchemy).
2.  Write the repository class with a `save_document` method.
3.  Update the consumer's logic to call this repository.

**✅ Definition of Done:**
*   **Integration Test:** Upload a document via the API. Verify that a new row corresponding to that document appears in your PostgreSQL `documents` table.
*   Unit tests for the `PostgreSQLRepository` are written (potentially using a test database).

---

### Sprint 3: RAG Pipeline Part 1 - Parsing and Chunking

**Goal:** Begin the RAG processing flow. Take the raw document, parse its content, break it into chunks, and save those chunks.

**Components to Build:**
*   **Document Parser Factory (`core` Layer):** Implement the factory. Start with a very simple `TextParser` that just reads `.txt` files.
*   **Semantic Chunker (`core` Layer):** Implement the `SemanticChunker`. For now, it can be a simple fixed-size chunker. Don't worry about embeddings yet.
*   **Prefect Orchestrator (`infra` Layer):** Create your first Prefect flow. The Kafka consumer will now trigger this flow. The flow's tasks will be: 1) Parse the document, 2) Chunk the document, 3) Save the chunks.
*   **Update Persistence:** Extend your `PersistenceManager` and repository to handle saving `Chunk` objects.

**Implementation Steps:**
1.  Build the `TextParser`.
2.  Build the basic `SemanticChunker`.
3.  Write the Prefect flow that coordinates these two steps.
4.  Modify the Kafka Consumer to trigger the Prefect flow instead of directly saving the document.

**✅ Definition of Done:**
*   **Integration Test:** Upload a `.txt` file. Verify that a Prefect flow run is created and completes successfully. Check the PostgreSQL database to see the document's chunks saved in a `chunks` table, linked by a `document_id`.
*   Unit tests for the `TextParser` and `SemanticChunker` are written.

---

### Sprint 4: RAG Pipeline Part 2 - Embeddings and Vector Storage

**Goal:** Complete the RAG ingestion pipeline by generating embeddings and storing them in ChromaDB.

**Components to Build:**
*   **Embedding Service:** Create a simple wrapper class that calls an embedding model (e.g., from Hugging Face, OpenAI).
*   **Update Prefect Flow:** Add a new task to your Prefect flow: after saving chunks to Postgres, get the text for each chunk, generate an embedding, and save it.
*   **ChromaDB Repository:** Create a repository implementation for saving chunks and their embeddings to ChromaDB.

**Implementation Steps:**
1.  Choose an embedding model and build your service wrapper.
2.  Write the ChromaDB repository class with a `save_chunks` method.
3.  Add the embedding generation and vector store saving steps to your Prefect flow.

**✅ Definition of Done:**
*   **Integration Test:** Upload a `.txt` file. After the flow completes, connect to your ChromaDB instance and verify that vectors corresponding to the document's chunks have been added to your collection.
*   Unit tests for the ChromaDB repository are written.

---

### Sprint 5: The Payoff - RAG Query Engine

**Goal:** Finally, get information *out* of the system. Build the API to query your RAG pipeline.

**Components to Build:**
*   **RAG Query Engine (`query` Layer):** Implement the class. It will have a `query()` method that: 1) Takes a user query string, 2) Generates an embedding for the query, 3) Queries ChromaDB to find the most similar chunks, 4) Passes the chunks and query to an LLM to generate an answer.
*   **Query API Endpoint:** Add a new `/query` endpoint to your FastAPI application.

**Implementation Steps:**
1.  Build the `query` method logic in the `RAGQueryEngine`.
2.  Create the `/query` endpoint that uses the engine.

**✅ Definition of Done:**
*   **End-to-End Test:**
    1.  Clear your databases.
    2.  Upload a specific `.txt` document with known facts (e.g., "The sky is blue.").
    3.  Call the `/query` endpoint with a relevant question ("What color is the sky?").
    4.  Verify that the API returns a correct, LLM-generated answer.

---

### Future Sprints: Building on the Foundation

Once you have a fully functional RAG pipeline, you can start layering on the more advanced features.

*   **Sprint 6: Expanding Parsers:** Implement the `PDFParser`, `ImageParser`, and `DocxParser`. Add logic to your `DocumentParserFactory` to correctly route files.
*   **Sprint 7: Structured Extraction Part 1 - Field Discovery:** Build the `OrchestratorAgent` and `FieldDiscoveryAgent`. The goal for this sprint is to trigger a flow that takes a document and produces a JSON `ExtractionSchema`.
*   **Sprint 8: Structured Extraction Part 2 - The Agent Swarm:** Build the logic for scaling agents based on document size and the `ExtractionAgent` that performs the actual extraction using the schema.
*   **Sprint 9: Hybrid Querying:** Implement the `Structured Query Workflow`. Update the `RAGQueryEngine` to trigger this workflow and merge the results for an enhanced response.
*   **Sprint 10: Monitoring and Evaluation:** Integrate `WandB` for monitoring and implement the `RagasEvaluator` to measure the performance of your RAG pipeline.