import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import os
from fastapi import HTTPException
import logging
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool
connection_pool = None

def init_connection_pool():
    """Initialize connection pool for NeonDB"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.getenv("NEON_HOST"),
            database=os.getenv("NEON_DATABASE"),
            user=os.getenv("NEON_USER"),
            password=os.getenv("NEON_PASSWORD"),
            port=int(os.getenv("NEON_PORT", 5432)),
            sslmode=os.getenv("NEON_SSL_MODE", "require"),
            # Connection timeout
            connect_timeout=10,
            # Keep connections alive
            keepalives_idle=600,
            keepalives_interval=30,
            keepalives_count=3
        )
        logger.info("✅ NeonDB connection pool initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool: {e}")
        return False

@contextmanager
def get_db_connection():
    """Get database connection from pool with context manager"""
    if not connection_pool:
        if not init_connection_pool():
            raise HTTPException(status_code=500, detail="Database connection pool not available")
    
    connection = None
    try:
        connection = connection_pool.getconn()
        yield connection
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
    finally:
        if connection:
            connection_pool.putconn(connection)

def get_db_connection_direct():
    """Direct connection method for backwards compatibility"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("NEON_HOST"),
            database=os.getenv("NEON_DATABASE"),
            user=os.getenv("NEON_USER"),
            password=os.getenv("NEON_PASSWORD"),
            port=int(os.getenv("NEON_PORT", 5432)),
            sslmode=os.getenv("NEON_SSL_MODE", "require"),
            cursor_factory=RealDictCursor
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def drop_existing_tables():
    """Drop existing tables to avoid conflicts"""
    with get_db_connection() as connection:
        try:
            cursor = connection.cursor()
            
            # Drop tables in reverse order of dependencies
            tables_to_drop = [
                'qnas',
                'documents', 
                'sessions',
                'accounts',
                'verification_tokens',
                'users'
            ]
            
            for table in tables_to_drop:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                logger.info(f"✅ Dropped table {table} if it existed")
            
            connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to drop existing tables: {e}")
            connection.rollback()
            raise

def init_db():
    """Initialize database tables matching Prisma schema"""
    try:
        # First drop existing tables to avoid conflicts
        drop_existing_tables()
        
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            # Create users table first (no foreign keys)
            cursor.execute('''
                CREATE TABLE "users" (
                    id TEXT NOT NULL PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE,
                    email_verified TIMESTAMPTZ,
                    image TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            ''')
            
            # Create index on email
            cursor.execute('CREATE INDEX "users_email_idx" ON "users"("email")')
            logger.info("✅ Created users table")
            
            # Create accounts table
            cursor.execute('''
                CREATE TABLE "accounts" (
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
            
            # Create index for accounts
            cursor.execute('CREATE INDEX "accounts_user_id_idx" ON "accounts"("user_id")')
            logger.info("✅ Created accounts table")
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE "sessions" (
                    id TEXT NOT NULL PRIMARY KEY,
                    session_token TEXT NOT NULL UNIQUE,
                    user_id TEXT NOT NULL,
                    expires TIMESTAMPTZ NOT NULL,
                    CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')
            
            # Create indexes for sessions
            cursor.execute('CREATE INDEX "sessions_user_id_idx" ON "sessions"("user_id")')
            cursor.execute('CREATE UNIQUE INDEX "sessions_session_token_key" ON "sessions"("session_token")')
            logger.info("✅ Created sessions table")
            
            # Create verification_tokens table
            cursor.execute('''
                CREATE TABLE "verification_tokens" (
                    identifier TEXT NOT NULL,
                    token TEXT NOT NULL,
                    expires TIMESTAMPTZ NOT NULL,
                    CONSTRAINT verification_tokens_identifier_token_key UNIQUE (identifier, token)
                )
            ''')
            logger.info("✅ Created verification_tokens table")
            
            # Create documents table
            cursor.execute('''
                CREATE TABLE "documents" (
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
            
            # Create indexes for documents
            cursor.execute('CREATE INDEX "documents_user_id_idx" ON "documents"("user_id")')
            cursor.execute('CREATE INDEX "documents_gcs_file_id_idx" ON "documents"("gcs_file_id")')
            logger.info("✅ Created documents table")
            
            # Create qnas table (equivalent to chat_history)
            cursor.execute('''
                CREATE TABLE "qnas" (
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
            
            # Create indexes for qnas
            cursor.execute('CREATE INDEX "qnas_user_id_document_id_idx" ON "qnas"("user_id", "document_id")')
            cursor.execute('CREATE INDEX "qnas_user_id_idx" ON "qnas"("user_id")')
            cursor.execute('CREATE INDEX "qnas_document_id_idx" ON "qnas"("document_id")')
            logger.info("✅ Created qnas table")
            
            # Create function to automatically update updated_at
            cursor.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            ''')
            
            # Create triggers for updated_at
            cursor.execute('''
                CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON "users"
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            ''')
            
            cursor.execute('''
                CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON "documents"
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            ''')
            
            connection.commit()
            logger.info("✅ Database tables initialized successfully with proper foreign key constraints")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def test_db_connection():
    """Test database connection and basic operations"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
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
        logger.error(f"❌ Database connection test failed: {e}")
        return False

def get_db_stats():
    """Get database statistics for monitoring"""
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            
            stats = {}
            
            # Get table counts
            tables = ['users', 'documents', 'qnas', 'accounts', 'sessions']
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                stats[f"{table}_count"] = count
            
            # Get database size
            cursor.execute('''
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            ''')
            
            result = cursor.fetchone()
            stats['database_size'] = result['db_size'] if result else '0 bytes'
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

# Initialize connection pool on module import
if not connection_pool:
    init_connection_pool()