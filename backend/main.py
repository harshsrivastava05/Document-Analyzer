import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import time
import traceback

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if not os.getenv("DISABLE_FILE_LOGGING") else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import services and routers
from database import init_db, test_db_connection, get_db_stats
from services.ai_services import init_ai_services
from routers import auth, upload, documents, chat, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Document Analyzer Backend...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        init_db()
        
        # Test database connection
        if not test_db_connection():
            raise Exception("Database connection test failed")
        
        # Initialize AI services
        logger.info("🤖 Initializing AI services...")
        init_ai_services()
        
        # Log startup success
        logger.info("✅ Application started successfully!")
        
        # Log database stats
        stats = get_db_stats()
        logger.info(f"📈 Database stats: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    yield
    
    # Shutdown logic
    logger.info("🛑 Shutting down application...")

# Create FastAPI app
app = FastAPI(
    title="AI Document Analyzer API",
    description="A powerful document processing and analysis API with AI-powered insights and RAG capabilities",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    lifespan=lifespan
)

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,*.vercel.app,*.netlify.app").split(",")
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring"""
    start_time = time.time()
    
    # Log request
    logger.info(f"📨 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for better error responses"""
    logger.error(f"❌ Unhandled exception in {request.method} {request.url.path}: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Don't expose internal errors in production
    if os.getenv("ENVIRONMENT", "development") == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(exc)}"}
        )

# HTTPException handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with better logging"""
    logger.warning(f"⚠️ HTTP {exc.status_code} in {request.method} {request.url.path}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(health.router, prefix="", tags=["Health"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "AI Document Analyzer API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs" if os.getenv("ENVIRONMENT", "development") == "development" else "disabled",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# API info endpoint
@app.get("/api/info", tags=["Info"])
async def api_info():
    """API information endpoint"""
    return {
        "api_name": "AI Document Analyzer",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "features": [
            "JWT Authentication",
            "Document Upload & Processing",
            "AI-Powered Analysis (Gemini)",
            "RAG Question Answering",
            "Vector Search (Pinecone)",
            "Embeddings (Cohere)",
            "Google Cloud Storage"
        ],
        "endpoints": {
            "auth": "/api/auth/{login,register}",
            "upload": "/api/upload",
            "documents": "/api/documents",
            "chat": "/api/{ask,chat-history}",
            "health": "/health"
        }
    }

# Monitoring endpoint
@app.get("/api/stats", tags=["Monitoring"])
async def get_stats():
    """Get application statistics"""
    try:
        db_stats = get_db_stats()
        return {
            "database": db_stats,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": {
                "database": "connected",
                "gemini": "initialized",
                "pinecone": "connected",
                "cohere": "connected",
                "gcs": "connected"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

if __name__ == "__main__":
    # Production-ready server configuration
    config = {
        "app": "main:app",
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", 8000)),
        "reload": os.getenv("ENVIRONMENT", "development") == "development",
        "workers": int(os.getenv("WORKERS", 1)),
        "access_log": os.getenv("ENABLE_ACCESS_LOG", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "info").lower(),
    }
    
    # SSL configuration for production
    if os.getenv("SSL_KEYFILE") and os.getenv("SSL_CERTFILE"):
        config.update({
            "ssl_keyfile": os.getenv("SSL_KEYFILE"),
            "ssl_certfile": os.getenv("SSL_CERTFILE")
        })
        logger.info("🔒 SSL enabled")
    
    logger.info(f"🚀 Starting server with config: {config}")
    uvicorn.run(**config)