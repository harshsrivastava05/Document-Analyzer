import time
import traceback
from fastapi import Request, HTTPException
from core.logging_config import logger

async def log_requests_with_pool_monitoring(request: Request, call_next):
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"📨 {request.method} {request.url.path} - Client: {client_host}")
    request_id = f"{int(start_time * 1000000)}"

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_emoji = "✅" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"
        logger.info(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s - ID: {request_id}")
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(f"❌ Error handling request {request.url.path}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")
