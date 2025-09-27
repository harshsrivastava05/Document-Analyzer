import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import logging
import threading
from fastapi import HTTPException
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
connection_pool = None
pool_lock = threading.RLock()

def parse_database_url(database_url: str) -> dict:
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'sslmode': 'require'
    }

def init_connection_pool():
    global connection_pool
    with pool_lock:
        if connection_pool is not None:
            return True
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                db_config = parse_database_url(database_url)
            else:
                db_config = {
                    'host': os.getenv("NEON_HOST", "localhost"),
                    'database': os.getenv("NEON_DATABASE", "postgres"),
                    'user': os.getenv("NEON_USER", "postgres"),
                    'password': os.getenv("NEON_PASSWORD", ""),
                    'port': int(os.getenv("NEON_PORT", 5432)),
                    'sslmode': os.getenv("NEON_SSL_MODE", "require")
                }

            min_conn = int(os.getenv("DB_POOL_MIN", 2))
            max_conn = int(os.getenv("DB_POOL_MAX", 6))

            connection_pool = ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                **db_config,
                connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", 30)),
                keepalives_idle=600,
                keepalives_interval=30,
                keepalives_count=3,
                application_name="doc-analyzer-backend"
            )

            test_conn = connection_pool.getconn()
            with test_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            connection_pool.putconn(test_conn)

            logger.info("✅ Database pool initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize pool: {e}")
            connection_pool = None
            return False

def get_db_connection():
    from contextlib import contextmanager
    @contextmanager
    def _get_conn():
        if not connection_pool and not init_connection_pool():
            raise HTTPException(status_code=500, detail="DB pool not available")
        connection = None
        try:
            connection = connection_pool.getconn()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            yield connection
            if connection.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                connection.commit()
        except Exception as e:
            if connection and connection.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                connection.rollback()
            raise e
        finally:
            if connection:
                try:
                    if connection.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                        connection.rollback()
                    connection_pool.putconn(connection)
                except Exception as e:
                    logger.error(f"❌ Error returning connection: {e}")
    return _get_conn()