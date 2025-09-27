from db.connection import get_db_connection, logger
from psycopg2.extras import RealDictCursor

def check_tables_exist():
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('users','accounts','sessions','documents','qnas','verification_tokens')
                """)
                return cursor.fetchone()['count'] == 6
    except Exception as e:
        logger.error(f"❌ Failed to check tables: {e}")
        return False

def create_tables_if_not_exist():
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''CREATE TABLE IF NOT EXISTS "users" (id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE)''')
                # (other CREATE statements omitted for brevity)
                logger.info("✅ Tables verified/created")
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        raise

def init_db():
    if check_tables_exist():
        logger.info("✅ Tables exist, skipping")
    else:
        create_tables_if_not_exist()