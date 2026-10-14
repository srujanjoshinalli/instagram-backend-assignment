# Image Storage API

A Python-based image storage REST API built with AWS S3, DynamoDB, and AWS Lambda-compatible request handling. Local development and integration testing use LocalStack, with FastAPI providing a local HTTP server.

## Features

- Upload images with metadata and optional captions
- Store image files in Amazon S3
- Store image metadata in DynamoDB
- Retrieve image metadata by ID
- Download stored images
- List images by owner or content type
- Paginate listing results
- Delete images and associated metadata
- Unit tests, handler tests, and LocalStack integration tests

## Tech Stack

- Python
- AWS Lambda-compatible handler
- Amazon S3
- Amazon DynamoDB
- LocalStack
- FastAPI and Uvicorn
- boto3
- pytest
- Docker Compose

## Architecture

```text
Client
  |
  v
FastAPI Local HTTP Server
  |
  v
Lambda-Compatible Request Handler
  |
  v
Image Service
  |                  |
  v                  v
Amazon S3        DynamoDB
(image files)    (metadata)
```

LocalStack provides local S3 and DynamoDB-compatible services for development and integration testing.

## Prerequisites

- Python 3.11 or newer
- Docker Desktop
- Docker Compose
- AWS CLI (optional, useful for inspecting LocalStack resources)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/srujanjoshinalli/instagram-backend-assignment
cd image-storage-api
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start LocalStack

```bash
docker compose up -d
```

Check its health:

```bash
curl http://localhost:4566/_localstack/health
```

### 4. Configure local AWS credentials

These credentials are for LocalStack development only. Do not use real AWS credentials for this local setup.

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566
export IMAGE_BUCKET=image-storage-local
export IMAGE_TABLE=Images
```

### 5. Initialize storage resources

```bash
python infrastructure/init_local.py
```

This initializes the S3 bucket and DynamoDB table required by the application.

### 6. Run tests

```bash
pytest -v
```

The LocalStack integration test requires LocalStack to be running.

### 7. Start the API

```bash
uvicorn src.local_server:app --reload --port 8000
```

The local API is available at `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/images` | Upload an image |
| GET | `/images?owner_id={owner_id}` | List images for an owner |
| GET | `/images?content_type={type}` | List images by content type |
| GET | `/images/{image_id}` | Get image metadata |
| GET | `/images/{image_id}/download` | Download an image |
| DELETE | `/images/{image_id}` | Delete an image |

### Upload an image

The upload endpoint accepts a JSON request containing Base64-encoded image data.

```bash
IMAGE_BASE64=$(base64 < /path/to/image.png | tr -d '\n')

curl -X POST http://localhost:8000/images \
  -H "Content-Type: application/json" \
  -d "{
    \"owner_id\": \"user-123\",
    \"filename\": \"image.png\",
    \"content_type\": \"image/png\",
    \"image_base64\": \"$IMAGE_BASE64\",
    \"caption\": \"Sample image\"
  }"
```

The response includes the generated image ID, owner ID, S3 key, content type, file size, caption, and creation timestamp.

### Get metadata

```bash
curl http://localhost:8000/images/<IMAGE_ID>
```

### Download an image

```bash
curl http://localhost:8000/images/<IMAGE_ID>/download -o downloaded.png
```

### List images

```bash
curl "http://localhost:8000/images?owner_id=user-123"
```

### Delete an image

```bash
curl -X DELETE http://localhost:8000/images/<IMAGE_ID>
```

A successful deletion returns HTTP `204 No Content`.

## Project Structure

```text
image-storage-api/
├── infrastructure/
│   └── init_local.py
├── src/
│   ├── config.py
│   ├── handler.py
│   ├── local_server.py
│   ├── repositories/
│   └── services/
│       └── image_service.py
├── tests/
│   ├── test_handler.py
│   ├── test_image_service.py
│   └── test_localstack_integration.py
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
├── .gitignore
└── README.md
```