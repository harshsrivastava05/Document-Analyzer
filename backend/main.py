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
import signal
import sys

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
from database import init_db, test_db_connection, get_db_stats, cleanup_connection_pool
from services.ai_services import init_ai_services
from routers import auth, upload, documents, chat, health

# Global flag for graceful shutdown
shutdown_event = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_event
    logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
    shutdown_event = True
    cleanup_connection_pool()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with enhanced error handling and retry logic"""
    logger.info("🚀 Starting Document Analyzer Backend...")
    
    max_startup_retries = 3
    startup_success = False
    
    for attempt in range(max_startup_retries):
        try:
            logger.info(f"📊 Initializing database (attempt {attempt + 1}/{max_startup_retries})...")
            
            # Initialize database with retry logic
            init_db()
            
            # Test database connection with multiple attempts
            db_test_attempts = 3
            db_connected = False
            
            for db_attempt in range(db_test_attempts):
                if test_db_connection():
                    db_connected = True
                    logger.info("✅ Database connection verified")
                    break
                else:
                    if db_attempt < db_test_attempts - 1:
                        logger.warning(f"Database test failed, retrying in 2 seconds... (attempt {db_attempt + 1}/{db_test_attempts})")
                        await asyncio.sleep(2)
                    else:
                        raise Exception("Database connection test failed after multiple attempts")
            
            if not db_connected:
                raise Exception("Failed to establish stable database connection")
            
            # Initialize AI services
            logger.info("🤖 Initializing AI services...")
            try:
                init_ai_services()
                logger.info("✅ AI services initialized successfully")
            except Exception as ai_error:
                logger.warning(f"⚠️ AI services initialization failed: {ai_error}")
                logger.warning("Application will continue without AI services")
            
            # Log startup success
            logger.info("✅ Application started successfully!")
            startup_success = True
            break
            
        except Exception as e:
            logger.error(f"❌ Application startup attempt {attempt + 1} failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if attempt < max_startup_retries - 1:
                retry_delay = 5 * (attempt + 1)  # Progressive delay: 5s, 10s, 15s
                logger.info(f"Retrying application startup in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ Application startup failed after {max_startup_retries} attempts")
                raise
    
    if not startup_success:
        raise Exception("Application failed to start after all retry attempts")
    
    try:
        # Log database stats for monitoring
        stats = get_db_stats()
        logger.info(f"📈 Database stats: {stats}")
    except Exception as stats_error:
        logger.warning(f"Could not retrieve database stats: {stats_error}")
    
    yield
    
    # Shutdown logic
    logger.info("🛑 Shutting down application...")
    try:
        cleanup_connection_pool()
        logger.info("✅ Graceful shutdown completed")
    except Exception as shutdown_error:
        logger.error(f"Error during shutdown: {shutdown_error}")

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
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,*.vercel.app,*.netlify.app,*.railway.app").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# CORS Middleware with more permissive settings for development
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware with better performance monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring with performance metrics"""
    start_time = time.time()
    
    # Extract client info safely
    client_host = "unknown"
    if request.client:
        client_host = request.client.host
    
    # Log request with more details
    logger.info(f"📨 {request.method} {request.url.path} - Client: {client_host}")
    
    # Add request ID for tracing (simple timestamp-based)
    request_id = f"{int(start_time * 1000000)}"  # Microsecond timestamp
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response with performance metrics
        status_emoji = "✅" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"
        logger.info(f"{status_emoji} {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s - ID: {request_id}")
        
        # Add performance and tracing headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # Alert on slow requests (>5 seconds)
        if process_time > 5.0:
            logger.warning(f"🐌 Slow request detected: {request.method} {request.url.path} took {process_time:.3f}s")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s - ID: {request_id}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return appropriate error response
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail="Internal server error")

# Global exception handler with better error reporting
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for better error responses"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(f"❌ Unhandled exception in {request.method} {request.url.path} (ID: {request_id}): {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Don't expose internal errors in production
    if os.getenv("ENVIRONMENT", "development") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error", 
                "request_id": request_id,
                "timestamp": time.time()
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error: {str(exc)}", 
                "request_id": request_id,
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        )

# HTTPException handler with better logging
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with better logging"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    if exc.status_code >= 500:
        logger.error(f"❌ HTTP {exc.status_code} in {request.method} {request.url.path} (ID: {request_id}): {exc.detail}")
    else:
        logger.warning(f"⚠️ HTTP {exc.status_code} in {request.method} {request.url.path} (ID: {request_id}): {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail, 
            "request_id": request_id,
            "timestamp": time.time()
        }
    )

# Health check middleware - simple endpoint that doesn't require DB
@app.get("/ping", tags=["Health"])
async def ping():
    """Simple ping endpoint for load balancer health checks"""
    return {"status": "ok", "timestamp": time.time()}

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
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": time.time()
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
            "health": "/health",
            "ping": "/ping"
        },
        "cors_origins": cors_origins,
        "allowed_hosts": allowed_hosts
    }

# Monitoring endpoint with error handling
@app.get("/api/stats", tags=["Monitoring"])
async def get_stats():
    """Get application statistics with graceful error handling"""
    try:
        db_stats = get_db_stats()
        return {
            "database": db_stats,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": {
                "database": "connected" if db_stats else "unavailable",
                "gemini": "initialized",
                "pinecone": "connected",
                "cohere": "connected",
                "gcs": "connected"
            },
            "timestamp": time.time(),
            "uptime": time.time()  # Simple uptime approximation
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        # Return partial stats instead of failing completely
        return {
            "database": {"error": str(e)},
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": {
                "database": "error",
                "gemini": "unknown",
                "pinecone": "unknown", 
                "cohere": "unknown",
                "gcs": "unknown"
            },
            "timestamp": time.time(),
            "error": "Failed to retrieve complete statistics"
        }

if __name__ == "__main__":
    # Import asyncio for the lifespan manager
    import asyncio
    
    # Production-ready server configuration
    config = {
        "app": "main:app",
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", 8000)),
        "reload": os.getenv("ENVIRONMENT", "development") == "development",
        "workers": int(os.getenv("WORKERS", 1)),
        "access_log": os.getenv("ENABLE_ACCESS_LOG", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "info").lower(),
        # Enhanced timeout settings
        "timeout_keep_alive": int(os.getenv("TIMEOUT_KEEP_ALIVE", 30)),
        "timeout_graceful_shutdown": int(os.getenv("TIMEOUT_GRACEFUL_SHUTDOWN", 30)),
    }
    
    # SSL configuration for production
    if os.getenv("SSL_KEYFILE") and os.getenv("SSL_CERTFILE"):
        config.update({
            "ssl_keyfile": os.getenv("SSL_KEYFILE"),
            "ssl_certfile": os.getenv("SSL_CERTFILE")
        })
        logger.info("🔒 SSL enabled")
    
    logger.info(f"🚀 Starting server with config: {config}")
    
    try:
        uvicorn.run(**config)
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        cleanup_connection_pool()
        sys.exit(1)