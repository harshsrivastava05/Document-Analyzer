from db.connection import connection_pool, pool_lock, logger

def cleanup_connection_pool():
    global connection_pool
    with pool_lock:
        if connection_pool:
            try:
                logger.info("🧹 Cleaning up connection pool...")
                connection_pool.closeall()
                connection_pool = None
            except Exception as e:
                logger.error(f"❌ Cleanup failed: {e}")
                connection_pool = None
