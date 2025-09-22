A modular FastAPI backend for document processing with AI-powered analysis and RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Modular Architecture**: Clean separation of concerns with routers, services, and models
- **Google Cloud Storage**: Secure file storage and management
- **AI-Powered Analysis**: Document analysis using Google's Gemini AI
- **RAG Pipeline**: Question-answering using Pinecone vector database and Cohere embeddings
- **JWT Authentication**: Secure user authentication and authorization
- **MySQL Database**: Persistent storage for users, documents, and chat history

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── database.py            # Database connection and initialization
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── models/
│   └── schemas.py        # Pydantic models and schemas
├── services/
│   ├── auth_service.py   # Authentication and JWT handling
│   ├── ai_services.py    # AI services (Gemini, Pinecone, Cohere)
│   └── gcs_service.py    # Google Cloud Storage operations
└── routers/
    ├── auth.py           # Authentication endpoints
    ├── upload.py         # Document upload and processing
    ├── documents.py      # Document management endpoints
    ├── chat.py           # Chat and Q&A endpoints
    └── health.py         # Health check endpoint
```

## Setup Instructions

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

### 3. Database Setup

Make sure MySQL is running and create a database:

```sql
CREATE DATABASE docanalyzer;
```

The application will automatically create the required tables on startup.

### 4. Google Cloud Storage Setup

1. Create a GCS bucket
2. Create a service account with Storage Admin permissions
3. Download the service account key JSON file
4. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### 5. AI Services Setup

- **Gemini AI**: Get API key from Google AI Studio
- **Pinecone**: Create index and get API key
- **Cohere**: Get API key from Cohere dashboard

### 6. Run the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health
- `GET /health` - Health check

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Documents
- `POST /api/upload` - Upload and process document
- `GET /api/documents` - Get user's documents
- `GET /api/documents/{id}/download` - Download document
- `DELETE /api/documents/{id}` - Delete document

### Chat
- `POST /api/ask` - Ask question about document
- `GET /api/chat-history` - Get chat history for document

## Key Changes Made

1. **Modular Structure**: Split the monolithic `main.py` into focused modules
2. **Google Cloud Storage**: Replaced Google Drive with GCS for better scalability
3. **Fixed API Endpoints**: Aligned backend endpoints with frontend expectations
4. **Better Error Handling**: Comprehensive error handling and logging
5. **Database Schema**: Updated to support GCS file IDs and improved chat history
6. **Authentication**: Proper JWT-based authentication system
7. **Type Safety**: Added Pydantic models for request/response validation

## Frontend Compatibility

The backend now properly supports all the endpoints used by your frontend:

- `/api/proxy/upload` → `/api/upload`
- `/api/proxy/documents` → `/api/documents`
- `/api/proxy/ask` → `/api/ask`  
- `/api/proxy/chat-history` → `/api/chat-history`
- Document download endpoint matches frontend expectations

## Deployment Notes

- Use base64 encoded service account key for cloud deployment
- Set appropriate CORS origins for production
- Use environment variables for all sensitive configuration
- Consider using connection pooling for database connections in production