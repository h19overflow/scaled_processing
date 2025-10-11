 1. Database Layer (models.py)
    - Added JobStatus enum (QUEUED, PROCESSING, COMPLETED, FAILED)
    - Added JobModel table to track jobs in PostgreSQL
  2. Kafka Infrastructure (topics_setup.py)
    - Added job_status_updates topic for event-driven status tracking
  3. Database Management (connection_manager.py)
    - create_job(job_id, document_name, file_path) - Creates job with QUEUED status
    - get_job(job_id) - Retrieves job by ID
    - update_job_status(job_id, status, error, bill_data) - Updates job status
  4. Job Status Consumer (job_status_consumer.py)
    - Listens to job_status_updates topic
    - Updates PostgreSQL job records when status changes
    - Decouples pipeline from API layer
  5. API Endpoint Updates (document_processing_endpoints.py)
    - Returns HTTP 202 (Accepted) for async requests
    - Adds Retry-After: 5 header (5-second polling interval)
    - Creates job record before publishing to Kafka
    - Includes job_id in Kafka messages
  6. Pipeline Integration
    - file_detected_consumer.py: Publishes "PROCESSING" status when starting
    - document_processing_flow.py: Propagates job_id through the pipeline
    - document_pipeline_completed_consumer.py: Publishes "COMPLETED"/"FAILED" with bill data

  How It Works:

  Client → POST /process/async
           ↓
       [API creates job record (QUEUED)]
           ↓
       [Publishes to file_detected topic]
           ↓
       [Returns 202 + Retry-After: 5 + job_id]

  FileDetectedConsumer → Processes file
           ↓
       [Publishes "PROCESSING" to job_status_updates]
           ↓
  JobStatusConsumer → Updates PostgreSQL (status=PROCESSING)

  Pipeline Completes → StructuringConsumer
           ↓
       [Publishes "COMPLETED" + bill_data to job_status_updates]
           ↓
  JobStatusConsumer → Updates PostgreSQL (status=COMPLETED)

  Client → GET /status/{job_id} every 5 seconds
           ↓
       [Reads from PostgreSQL]
           ↓
       [Returns status + bill_data when completed]

  Next Steps:

  1. Run migrations to create the jobs table:
  # The ConnectionManager.create_tables() will handle this
  2. Create the Kafka topic:
  python -m src.backend.doc_processing_system.messaging.topics_setup
  3. Start the JobStatusConsumer:
  python -m src.backend.doc_processing_system.messaging.job_status_consumer
  4. Test the flow by uploading a document to /api/v1/process/async and polling /api/v1/status/{job_id}

  The system now uses your existing Kafka infrastructure for job tracking - no need to reinvent the wheel! 🎉