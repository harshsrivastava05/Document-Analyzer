from db.connection import get_db_connection, logger, connection_pool
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException

def ensure_user_exists_optimized(user_id: str):
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''INSERT INTO "users" (id, created_at, updated_at)
                    VALUES (%s, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING RETURNING id''', (user_id,))
                cursor.fetchone()
                return True
    except Exception as e:
        logger.error(f"❌ Failed to ensure user: {e}")
        raise HTTPException(status_code=500, detail="Failed to init user")

def test_db_connection():
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT 1 as test")
                return cursor.fetchone()['test'] == 1
    except Exception as e:
        logger.error(f"❌ Test connection failed: {e}")
        return False

def get_db_stats():
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''SELECT COUNT(*) as users_count FROM "users"''')
                stats = dict(cursor.fetchone())
                if connection_pool:
                    stats.update({
                        'pool_min': connection_pool.minconn,
                        'pool_max': connection_pool.maxconn
                    })
                return stats
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}")
        return {'error': str(e)}