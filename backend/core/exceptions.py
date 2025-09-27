import time
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from core.logging_config import logger

async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(f"❌ Unhandled exception in {request.method} {request.url.path} (ID: {request_id}): {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id, "timestamp": time.time()}
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID", "unknown")
    if exc.status_code >= 500:
        logger.error(f"❌ HTTP {exc.status_code}: {exc.detail}")
    else:
        logger.warning(f"⚠️ HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id, "timestamp": time.time()}
    )