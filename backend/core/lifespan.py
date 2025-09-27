import asyncio
import traceback
from contextlib import asynccontextmanager
from core.logging_config import logger
from db.schema import init_db
from db.utils import test_db_connection, get_db_stats
from db.cleanup import cleanup_connection_pool
from services.ai_services import init_ai_services

@asynccontextmanager
async def lifespan(app):
    logger.info("🚀 Starting Document Analyzer Backend...")

    max_startup_retries = 3
    for attempt in range(max_startup_retries):
        try:
            init_db()
            for _ in range(3):
                if test_db_connection():
                    logger.info("✅ Database connection verified")
                    break
                await asyncio.sleep(2)

            try:
                init_ai_services()
                logger.info("✅ AI services initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ AI services init failed: {e}")

            logger.info("✅ Application started successfully!")
            break
        except Exception as e:
            logger.error(f"❌ Startup attempt {attempt+1} failed: {e}")
            logger.error(traceback.format_exc())
            if attempt == max_startup_retries - 1:
                raise
            await asyncio.sleep(5 * (attempt + 1))

    try:
        stats = get_db_stats()
        logger.info(f"📈 Database stats: {stats}")
    except Exception as e:
        logger.warning(f"Could not fetch DB stats: {e}")

    yield

    logger.info("🛑 Shutting down application...")
    cleanup_connection_pool()
    logger.info("✅ Graceful shutdown completed")