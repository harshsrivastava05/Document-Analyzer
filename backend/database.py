# backend/database.py (UPDATED VERSION)
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import os
from fastapi import HTTPException
import logging
from contextlib import contextmanager
from urllib.parse import urlparse
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool
connection_pool = None

def parse_database_url(database_url: str) -> dict:
    """Parse DATABASE_URL into connection parameters"""
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],  # Remove leading '/'
        'user': parsed.username,
        'password': parsed.password,
        'sslmode': 'require'  # Default for cloud databases
    }

def init_connection_pool():
    """Initialize connection pool for database with improved settings"""
    global connection_pool
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Fallback to individual environment variables for backward compatibility
            db_config = {
                'host': os.getenv("NEON_HOST", "localhost"),
                'database': os.getenv("NEON_DATABASE", "postgres"),
                'user': os.getenv("NEON_USER", "postgres"),
                'password': os.getenv("NEON_PASSWORD", ""),
                'port': int(os.getenv("NEON_PORT", 5432)),
                'sslmode': os.getenv("NEON_SSL_MODE", "require")
            }
            logger.info("Using individual environment variables for database connection")
        else:
            db_config = parse_database_url(database_url)
            logger.info(f"Using DATABASE_URL for connection to {db_config['host']}")
        
        connection_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,  # Reduced from 20 for cloud databases
            **db_config,
            # Improved connection settings for cloud databases
            connect_timeout=30,  # Increased timeout
            keepalives_idle=300,   # 5 minutes - reduced from 600
            keepalives_interval=30,
            keepalives_count=3,
            # Additional settings for stability
            application_name='document_analyzer_backend',
            # Disable SSL compression for better compatibility
            sslcompression=0 if db_config.get('sslmode') == 'require' else None
        )
        logger.info("✅ Database connection pool initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool: {e}")
        return False

def test_connection(connection):
    """Test if a connection is still alive"""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except Exception:
        return False

@contextmanager
def get_db_connection():
    """Get database connection from pool with context manager and retry logic"""
    if not connection_pool:
        if not init_connection_pool():
            raise HTTPException(status_code=500, detail="Database connection pool not available")
    
    connection = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            connection = connection_pool.getconn()
            if connection is None:
                raise Exception("Failed to get connection from pool")
            
            # Test if connection is alive
            if not test_connection(connection):
                logger.warning("Dead connection detected, getting new one...")
                connection_pool.putconn(connection, close=True)
                connection = None
                retry_count += 1
                time.sleep(1)  # Brief pause before retry
                continue
                
            yield connection
            break
            
        except psycopg2.OperationalError as e:
            logger.error(f"Database operational error (attempt {retry_count + 1}): {str(e)}")
            if connection:
                connection_pool.putconn(connection, close=True)
                connection = None
            
            retry_count += 1
            if retry_count >= max_retries:
                raise HTTPException(status_code=500, detail=f"Database connection failed after {max_retries} attempts: {str(e)}")
            
            time.sleep(2 ** retry_count)  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            if connection:
                connection.rollback()
                connection_pool.putconn(connection, close=True)
                connection = None
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
    else:
        if connection:
            connection_pool.putconn(connection)

def get_db_connection_direct():
    """Direct connection method with retry logic"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
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
            
            connection = psycopg2.connect(
                cursor_factory=RealDictCursor,
                connect_timeout=30,
                **db_config
            )
            return connection
            
        except psycopg2.OperationalError as e:
            logger.error(f"Direct connection failed (attempt {retry_count + 1}): {str(e)}")
            retry_count += 1
            if retry_count >= max_retries:
                raise HTTPException(status_code=500, detail=f"Database connection failed after {max_retries} attempts: {str(e)}")
            time.sleep(2 ** retry_count)
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def check_tables_exist():
    """Check if database tables already exist"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('users', 'accounts', 'sessions', 'documents', 'qnas', 'verification_tokens')
                """)
                result = cursor.fetchone()
                table_count = result['count'] if result else 0
                # We expect 6 tables in total
                return table_count == 6
        except Exception as e:
            logger.error(f"Failed to check existing tables (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(2 ** attempt)
    return False

def create_tables_if_not_exist():
    """Create database tables only if they don't already exist"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Create users table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "users" (
                    id TEXT NOT NULL PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE,
                    email_verified TIMESTAMPTZ,
                    image TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            ''')
            
            # Create index on email if it doesn't exist
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "users_email_idx" ON "users"("email")
            ''')
            
            # Create accounts table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "accounts" (
                    id TEXT NOT NULL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_account_id TEXT NOT NULL,
                    refresh_token TEXT,
                    access_token TEXT,
                    expires_at INTEGER,
                    token_type TEXT,
                    scope TEXT,
                    id_token TEXT,
                    session_state TEXT,
                    CONSTRAINT accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT accounts_provider_provider_account_id_key UNIQUE (provider, provider_account_id)
                )
            ''')
            
            # Create index for accounts if it doesn't exist
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "accounts_user_id_idx" ON "accounts"("user_id")
            ''')
            
            # Create sessions table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "sessions" (
                    id TEXT NOT NULL PRIMARY KEY,
                    session_token TEXT NOT NULL UNIQUE,
                    user_id TEXT NOT NULL,
                    expires TIMESTAMPTZ NOT NULL,
                    CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')
            
            # Create indexes for sessions if they don't exist
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "sessions_user_id_idx" ON "sessions"("user_id")
            ''')
            
            # Create verification_tokens table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "verification_tokens" (
                    identifier TEXT NOT NULL,
                    token TEXT NOT NULL,
                    expires TIMESTAMPTZ NOT NULL,
                    CONSTRAINT verification_tokens_identifier_token_key UNIQUE (identifier, token)
                )
            ''')
            
            # Create documents table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "documents" (
                    id TEXT NOT NULL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    gcs_file_id TEXT NOT NULL,
                    gcs_file_path TEXT,
                    mime_type TEXT,
                    file_size INTEGER,
                    summary TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')
            
            # Create indexes for documents if they don't exist
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "documents_user_id_idx" ON "documents"("user_id")
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "documents_gcs_file_id_idx" ON "documents"("gcs_file_id")
            ''')
            
            # Create qnas table if it doesn't exist (equivalent to chat_history)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "qnas" (
                    id TEXT NOT NULL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT qnas_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT qnas_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')
            
            # Create indexes for qnas if they don't exist
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "qnas_user_id_document_id_idx" ON "qnas"("user_id", "document_id")
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "qnas_user_id_idx" ON "qnas"("user_id")
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS "qnas_document_id_idx" ON "qnas"("document_id")
            ''')
            
            # Create function to automatically update updated_at if it doesn't exist
            cursor.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            ''')
            
            # Create triggers for updated_at if they don't exist
            cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
                        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON "users"
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END$$;
            ''')
            
            cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_documents_updated_at') THEN
                        CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON "documents"
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END$$;
            ''')
            
            connection.commit()
            logger.info("✅ Database tables verified/created successfully")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def init_db():
    """Initialize database tables only if they don't exist - preserves existing data"""
    try:
        # Check if tables already exist
        if check_tables_exist():
            logger.info("✅ Database tables already exist, skipping initialization to preserve data")
            return
        
        logger.info("🏗️ Creating new database schema...")
        create_tables_if_not_exist()
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def test_db_connection():
    """Test database connection and basic operations"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(cursor_factory=RealDictCursor)
                
                # Test basic query
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                if result and result['test'] == 1:
                    logger.info("✅ Database connection test passed")
                    return True
                else:
                    logger.error("❌ Database connection test failed")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Database connection test failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(2 ** attempt)
    return False

def get_db_stats():
    """Get database statistics for monitoring"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            stats = {}
            
            # Get table counts
            tables = ['users', 'documents', 'qnas', 'accounts', 'sessions']
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) as count FROM "{table}"')
                    count = cursor.fetchone()['count']
                    stats[f"{table}_count"] = count
                except Exception as e:
                    logger.warning(f"Could not get count for table {table}: {e}")
                    stats[f"{table}_count"] = 0
            
            # Get database size
            try:
                cursor.execute('''
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                ''')
                
                result = cursor.fetchone()
                stats['database_size'] = result['db_size'] if result else '0 bytes'
            except Exception as e:
                logger.warning(f"Could not get database size: {e}")
                stats['database_size'] = 'unknown'
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

# Cleanup function for graceful shutdown
def cleanup_connection_pool():
    """Clean up connection pool on shutdown"""
    global connection_pool
    try:
        if connection_pool:
            connection_pool.closeall()
            connection_pool = None
            logger.info("✅ Connection pool cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up connection pool: {e}")

# Initialize connection pool on module import
if not connection_pool:
    init_connection_pool()