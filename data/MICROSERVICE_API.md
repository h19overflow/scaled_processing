# Document Processing Microservice API

## Overview

This microservice processes Malaysian utility bills and extracts structured data. It accepts PDF or image documents via REST API and returns extracted bill information including amount due, due date, invoice number, and other relevant fields.

## Architecture

```
┌─────────────────┐
│   API Client    │
└────────┬────────┘
         │ POST /api/v1/process
         ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Server                     │
│  ┌──────────────────────────────────────────┐  │
│  │ 1. Validate & save uploaded file         │  │
│  │ 2. Publish to Kafka: file_detected       │  │
│  │ 3. Wait for completion (with timeout)    │  │
│  │ 4. Return structured bill data           │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Kafka Broker  │
         └────────┬───────┘
                  │
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│  File Detected   │  │  Document Pipeline│
│  Consumer (x6)   │  │  Completed Consumer│
│                  │  │      (x6)         │
│  - OCR/Vision    │  │                  │
│  - Text Extract  │  │  - Structured    │
│  - Mineru        │  │    Extraction    │
│                  │  │  - DB Storage    │
└──────────────────┘  └──────────────────┘
```

## System Flow

1. **Upload**: Client uploads document via POST endpoint
2. **Storage**: File saved to temp directory with unique ID
3. **Kafka Publish**: Message published to `file_detected` topic
4. **Processing**:
   - FileDetectedConsumer picks up message → runs OCR/text extraction
   - Publishes to `document_pipeline_completed` topic
   - StructuringConsumer picks up message → runs structured extraction
   - Stores bill data in database
5. **Response**: API waits for completion, retrieves bill data, returns to client

## API Endpoints

### 1. Process Document (Synchronous)

**Endpoint**: `POST /api/v1/process`

**Description**: Upload a document and receive extracted bill data. Blocks until processing completes (max 120s timeout).

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  ```
  file: <binary file data>
  ```

**Response** (200 OK):
```json
{
  "status": "completed",
  "document_name": "GSPP_0602_202507_Billing_NEM.pdf",
  "job_id": "abc123-def456-ghi789",
  "bill_data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "document_name": "GSPP_0602_202507_Billing_NEM.pdf",
    "amount_due": 1255.75,
    "due_date": "2025-08-31T00:00:00",
    "issue_date": "2025-08-31T00:00:00",
    "status": "PENDING",
    "extracted_jsonb": {
      "postal_address": {
        "postal_address": "NO. 24, JALAN ALOI 3, KAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA, 42700 BANTING SELANGOR"
      },
      "invoice_number": {
        "invoice_number": "000271377327"
      },
      "biller_code": {
        "biller_code": "5454"
      }
    },
    "created_at": "2025-10-04T12:34:56.789Z",
    "updated_at": "2025-10-04T12:35:10.123Z",
    "version": 1
  },
  "error": null,
  "processed_at": "2025-10-04T12:35:10.456Z"
}
```

**Response** (408 Timeout):
```json
{
  "status": "processing",
  "document_name": "bill.pdf",
  "job_id": "abc123-def456-ghi789",
  "bill_data": null,
  "error": "Processing timeout - job still running. Use job_id to check status.",
  "processed_at": "2025-10-04T12:37:00.000Z"
}
```

**Response** (500 Error):
```json
{
  "status": "failed",
  "document_name": "corrupted.pdf",
  "job_id": "xyz789-abc123-def456",
  "bill_data": null,
  "error": "OCR extraction failed: Invalid PDF format",
  "processed_at": "2025-10-04T12:35:05.000Z"
}
```

---

### 2. Process Document (Async)

**Endpoint**: `POST /api/v1/process/async`

**Description**: Upload a document and receive job ID immediately. Client polls for completion.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  ```
  file: <binary file data>
  ```

**Response** (202 Accepted):
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Document queued for processing. Use GET /api/v1/status/{job_id} to check progress."
}
```

---

### 3. Check Job Status

**Endpoint**: `GET /api/v1/status/{job_id}`

**Description**: Check processing status and retrieve results when complete.

**Request**:
- Method: `GET`
- Path Parameter: `job_id` (string)

**Response** (200 OK - Processing):
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "processing",
  "document_name": "bill.pdf",
  "bill_data": null,
  "error": null,
  "created_at": "2025-10-04T12:34:56.000Z",
  "completed_at": null
}
```

**Response** (200 OK - Completed):
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "document_name": "bill.pdf",
  "bill_data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "document_name": "bill.pdf",
    "amount_due": 575.50,
    "due_date": "2025-09-30T00:00:00",
    "extracted_jsonb": { ... }
  },
  "error": null,
  "created_at": "2025-10-04T12:34:56.000Z",
  "completed_at": "2025-10-04T12:35:10.000Z"
}
```

**Response** (404 Not Found):
```json
{
  "detail": "Job not found: invalid-job-id"
}
```

---

### 4. Health Check

**Endpoint**: `GET /api/v1/health`

**Description**: Check microservice health and dependent services status.

**Request**:
- Method: `GET`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-04T12:00:00.000Z",
  "services": {
    "kafka": "connected",
    "database": "connected",
    "file_system": "accessible"
  },
  "version": "1.0.0"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "degraded",
  "timestamp": "2025-10-04T12:00:00.000Z",
  "services": {
    "kafka": "disconnected",
    "database": "connected",
    "file_system": "accessible"
  },
  "version": "1.0.0"
}
```

---

## Extracted Bill Fields

The microservice extracts the following fields from Malaysian utility bills:

| Field | Type | Description | Stored In |
|-------|------|-------------|-----------|
| `amount_due` | Decimal | Total amount due | Core column |
| `due_date` | DateTime | Payment due date | Core column |
| `issue_date` | DateTime | Bill issue date | Core column |
| `postal_address` | Object | Customer postal address | `extracted_jsonb` |
| `invoice_number` | Object | Invoice/bill number | `extracted_jsonb` |
| `biller_code` | Object | Biller code for payment | `extracted_jsonb` |

---

## Integration Examples

### cURL

**Synchronous Processing**:
```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/bill.pdf"
```

**Async Processing**:
```bash
# Upload
curl -X POST "http://localhost:8000/api/v1/process/async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/bill.pdf"

# Check status
curl -X GET "http://localhost:8000/api/v1/status/abc123-def456-ghi789"
```

**Health Check**:
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

---

### Python (requests)

```python
import requests

# Synchronous processing
with open('bill.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/process',
        files={'file': f}
    )

if response.status_code == 200:
    data = response.json()
    print(f"Amount Due: RM{data['bill_data']['amount_due']}")
    print(f"Due Date: {data['bill_data']['due_date']}")
else:
    print(f"Error: {response.json()['error']}")
```

```python
import requests
import time

# Async processing with polling
with open('bill.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/process/async',
        files={'file': f}
    )

job_id = response.json()['job_id']
print(f"Job ID: {job_id}")

# Poll for completion (max 2 minutes)
for _ in range(24):  # 24 * 5s = 120s
    status_response = requests.get(
        f'http://localhost:8000/api/v1/status/{job_id}'
    )
    status_data = status_response.json()

    if status_data['status'] == 'completed':
        print("Processing complete!")
        print(status_data['bill_data'])
        break
    elif status_data['status'] == 'failed':
        print(f"Processing failed: {status_data['error']}")
        break

    time.sleep(5)  # Wait 5 seconds before next poll
```

---

### JavaScript (fetch)

```javascript
// Synchronous processing
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/v1/process', {
  method: 'POST',
  body: formData
});

const result = await response.json();
if (result.status === 'completed') {
  console.log('Amount Due:', result.bill_data.amount_due);
  console.log('Due Date:', result.bill_data.due_date);
}
```

---

## Deployment

### Running the Microservice

The API server is integrated into the existing `run_all.py` script:

```bash
python -m scripts.run_all
```

This starts 4 processes:
1. File Watcher
2. Document Processors (6 consumers)
3. Structured Extractors (6 consumers)
4. **FastAPI Server (port 8000)**

### API Only Mode

To run only the API server (assumes Kafka consumers are running separately):

```bash
python -m uvicorn src.backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables

```bash
KAFKA_BROKER=localhost:9092
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
UPLOAD_DIR=./data/temp/uploads
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT_SECONDS=120
```

---

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `202 Accepted` - Async job accepted
- `400 Bad Request` - Invalid file or parameters
- `404 Not Found` - Job ID not found
- `408 Request Timeout` - Processing timeout (sync mode)
- `413 Payload Too Large` - File exceeds size limit
- `415 Unsupported Media Type` - Invalid file type
- `500 Internal Server Error` - Processing error
- `503 Service Unavailable` - Service degraded/unavailable

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| File too large | File exceeds MAX_FILE_SIZE_MB | Compress or split document |
| Invalid file type | Not PDF/image | Convert to supported format |
| Processing timeout | Complex document | Use async endpoint and poll |
| Kafka unavailable | Broker down | Check Kafka status, retry |
| OCR failed | Corrupted/encrypted PDF | Provide clean, unencrypted file |

---

## Performance & Limits

- **Max File Size**: 50 MB (configurable)
- **Supported Formats**: PDF, PNG, JPG, JPEG
- **Processing Time**: 10-60 seconds typical (depends on pages/quality)
- **Timeout (Sync)**: 120 seconds
- **Concurrent Requests**: Limited by Kafka consumers (6 document + 6 extraction)
- **Rate Limiting**: Recommended 10 req/sec per client

---

## Security Considerations

1. **File Validation**: Only accept PDF and image formats
2. **Size Limits**: Enforce MAX_FILE_SIZE_MB to prevent DoS
3. **Temporary Storage**: Clean up uploaded files after processing
4. **Input Sanitization**: Validate all file names and metadata
5. **Authentication**: Add API keys/JWT in production (not included in v1.0)
6. **HTTPS**: Use TLS in production deployments

---

## Monitoring & Observability

### Logs
- Request/response logs with correlation IDs
- Processing pipeline events
- Error tracking with stack traces

### Metrics (Future)
- Request rate
- Processing time (p50, p95, p99)
- Success/failure rate
- Queue depth

### Health Checks
- Use `/api/v1/health` for liveness probes
- Check Kafka/database connectivity

---

## Version History

- **v1.0.0** (2025-10-04)
  - Initial microservice release
  - Synchronous and async processing
  - Malaysian utility bill extraction
  - Core fields: amount_due, due_date, invoice_number, postal_address, biller_code
