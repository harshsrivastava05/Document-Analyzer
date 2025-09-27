# backend/database.py - FIXED VERSION
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import os
from fastapi import HTTPException
import logging
from contextlib import contextmanager
from urllib.parse import urlparse
import time
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool with thread safety
connection_pool = None
pool_lock = threading.RLock()  # Reentrant lock for thread safety

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
    """Initialize connection pool with optimized settings for high concurrency"""
    global connection_pool
    
    with pool_lock:
        if connection_pool is not None:
            logger.info("🔄 Connection pool already exists, skipping initialization")
            return True
            
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # Fallback to individual environment variables
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
            
            # OPTIMIZED connection pool configuration
            connection_pool = ThreadedConnectionPool(
                minconn=3,   # Minimum connections always available
                maxconn=20,  # Increased maximum connections for high concurrency
                **db_config,
                # Enhanced connection settings for reliability
                connect_timeout=30,
                # Keep connections alive - more aggressive settings
                keepalives_idle=300,     # 5 minutes before first keepalive
                keepalives_interval=10,  # Check every 10 seconds  
                keepalives_count=3,      # 3 failed keepalives = dead connection
                # Application identification
                application_name="doc-analyzer-backend"
            )
            
            # Test the pool immediately with proper cleanup
            test_conn = None
            try:
                test_conn = connection_pool.getconn()
                if test_conn:
                    with test_conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    logger.info("✅ Database connection pool initialized and tested successfully")
                    logger.info(f"📊 Pool configured: min={connection_pool.minconn}, max={connection_pool.maxconn}")
                else:
                    raise Exception("Failed to get test connection from pool")
            finally:
                if test_conn:
                    connection_pool.putconn(test_conn)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize connection pool: {e}")
            connection_pool = None
            return False

@contextmanager
def get_db_connection():
    """Enhanced database connection manager with better error handling and cleanup"""
    if not connection_pool:
        logger.warning("🔄 Connection pool not initialized, attempting to initialize...")
        if not init_connection_pool():
            raise HTTPException(status_code=500, detail="Database connection pool not available")
    
    connection = None
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Get connection from pool with timeout
            connection = connection_pool.getconn()
            if connection is None:
                raise Exception("Failed to get connection from pool - pool may be exhausted")
            
            # Enhanced connection health check
            if connection.closed != 0:  # 0 = connection is open
                logger.warning(f"🔄 Connection was closed (status: {connection.closed}), getting new one (attempt {attempt + 1})")
                try:
                    connection_pool.putconn(connection, close=True)
                except:
                    pass
                connection = None
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                continue
            
            # Quick health check with timeout
            try:
                with connection.cursor() as test_cursor:
                    # Set statement timeout for this connection
                    test_cursor.execute("SET statement_timeout = '30s'")
                    test_cursor.execute("SELECT 1")
                    test_cursor.fetchone()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logger.warning(f"🔄 Connection health check failed: {e}, getting new one (attempt {attempt + 1})")
                try:
                    connection_pool.putconn(connection, close=True)
                except:
                    pass
                connection = None
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                continue
            
            # Connection is healthy, yield it
            logger.debug(f"✅ Got healthy database connection (attempt {attempt + 1})")
            yield connection
            return
            
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError) as e:
            logger.warning(f"🔄 Database connection attempt {attempt + 1} failed: {e}")
            if connection:
                try:
                    connection_pool.putconn(connection, close=True)
                except:
                    pass
                connection = None
            
            if attempt < max_retries - 1:
                logger.info(f"🔄 Retrying database connection in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"❌ All {max_retries} database connection attempts failed")
                # Check pool status
                try:
                    logger.error(f"📊 Pool status - closed connections: {connection_pool.closed}")
                except:
                    logger.error("📊 Cannot check pool status - pool may be corrupted")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Database connection failed after {max_retries} attempts: {str(e)}"
                )
        
        except Exception as e:
            logger.error(f"❌ Unexpected database connection error: {str(e)}")
            if connection:
                try:
                    connection.rollback()
                    connection_pool.putconn(connection)
                except:
                    try:
                        connection_pool.putconn(connection, close=True)
                    except:
                        pass
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
        
        finally:
            # CRITICAL: Always return connection to pool
            if connection:
                try:
                    # Make sure we don't have any uncommitted transactions
                    if connection.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                        connection.rollback()
                    connection_pool.putconn(connection)
                    logger.debug("✅ Connection returned to pool")
                except Exception as cleanup_error:
                    logger.error(f"❌ Error returning connection to pool: {cleanup_error}")
                    try:
                        connection_pool.putconn(connection, close=True)
                        logger.debug("🗑️ Closed problematic connection")
                    except:
                        logger.error("❌ Failed to close problematic connection")

def get_db_connection_direct():
    """Direct connection method with enhanced retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
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
            
            # Enhanced connection settings
            db_config.update({
                'connect_timeout': 30,
                'keepalives_idle': 300,
                'keepalives_interval': 10,
                'keepalives_count': 3,
                'application_name': 'doc-analyzer-direct'
            })
            
            connection = psycopg2.connect(
                cursor_factory=RealDictCursor,
                **db_config
            )
            
            # Set connection-level timeout
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '30s'")
            
            return connection
        
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logger.warning(f"🔄 Direct connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"❌ All {max_retries} direct connection attempts failed")
                raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def check_tables_exist():
    """Check if database tables already exist with proper connection handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('users', 'accounts', 'sessions', 'documents', 'qnas', 'verification_tokens')
                    """)
                    result = cursor.fetchone()
                    table_count = result['count'] if result else 0
                    return table_count == 6
        except Exception as e:
            logger.warning(f"🔄 Failed to check existing tables (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"❌ Failed to check tables after {max_retries} attempts")
                return False

def create_tables_if_not_exist():
    """Create database tables with proper transaction handling"""
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # Use a single transaction for all table creation
                try:
                    # Create users table
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
                    
                    # Create indexes
                    cursor.execute('CREATE INDEX IF NOT EXISTS "users_email_idx" ON "users"("email")')
                    
                    # Create accounts table
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
                    
                    cursor.execute('CREATE INDEX IF NOT EXISTS "accounts_user_id_idx" ON "accounts"("user_id")')
                    
                    # Create sessions table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS "sessions" (
                            id TEXT NOT NULL PRIMARY KEY,
                            session_token TEXT NOT NULL UNIQUE,
                            user_id TEXT NOT NULL,
                            expires TIMESTAMPTZ NOT NULL,
                            CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
                        )
                    ''')
                    
                    cursor.execute('CREATE INDEX IF NOT EXISTS "sessions_user_id_idx" ON "sessions"("user_id")')
                    
                    # Create verification_tokens table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS "verification_tokens" (
                            identifier TEXT NOT NULL,
                            token TEXT NOT NULL,
                            expires TIMESTAMPTZ NOT NULL,
                            CONSTRAINT verification_tokens_identifier_token_key UNIQUE (identifier, token)
                        )
                    ''')
                    
                    # Create documents table
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
                    
                    # Create indexes for documents
                    cursor.execute('CREATE INDEX IF NOT EXISTS "documents_user_id_idx" ON "documents"("user_id")')
                    cursor.execute('CREATE INDEX IF NOT EXISTS "documents_gcs_file_id_idx" ON "documents"("gcs_file_id")')
                    
                    # Create qnas table
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
                    
                    # Create indexes for qnas
                    cursor.execute('CREATE INDEX IF NOT EXISTS "qnas_user_id_document_id_idx" ON "qnas"("user_id", "document_id")')
                    cursor.execute('CREATE INDEX IF NOT EXISTS "qnas_user_id_idx" ON "qnas"("user_id")')
                    cursor.execute('CREATE INDEX IF NOT EXISTS "qnas_document_id_idx" ON "qnas"("document_id")')
                    
                    # Create function and triggers for updated_at
                    cursor.execute('''
                        CREATE OR REPLACE FUNCTION update_updated_at_column()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            NEW.updated_at = NOW();
                            RETURN NEW;
                        END;
                        $$ language 'plpgsql';
                    ''')
                    
                    # Create triggers
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
                    
                    # Commit all changes
                    connection.commit()
                    logger.info("✅ Database tables verified/created successfully")
                    
                except Exception as e:
                    connection.rollback()
                    raise e
                    
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def init_db():
    """Initialize database tables"""
    try:
        if check_tables_exist():
            logger.info("✅ Database tables already exist, skipping initialization")
            return
        
        logger.info("🏗️ Creating new database schema...")
        create_tables_if_not_exist()
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def test_db_connection():
    """Test database connection"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_db_connection() as connection:
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT 1 as test")
                    result = cursor.fetchone()
                    
                    if result and result['test'] == 1:
                        logger.info("✅ Database connection test passed")
                        return True
                    else:
                        logger.error("❌ Database connection test failed")
                        return False
                        
        except Exception as e:
            logger.warning(f"❌ Database connection test failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"❌ Database connection test failed after {max_retries} attempts")
                return False

def get_db_stats():
    """Get database statistics with proper connection handling"""
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
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
                    cursor.execute('SELECT pg_size_pretty(pg_database_size(current_database())) as db_size')
                    result = cursor.fetchone()
                    stats['database_size'] = result['db_size'] if result else '0 bytes'
                except Exception as e:
                    logger.warning(f"Could not get database size: {e}")
                    stats['database_size'] = 'unknown'
                
                # Add connection pool stats
                if connection_pool:
                    try:
                        stats['pool_min_connections'] = connection_pool.minconn
                        stats['pool_max_connections'] = connection_pool.maxconn
                        stats['pool_closed'] = connection_pool.closed
                    except:
                        pass
                
                return stats
                
    except Exception as e:
        logger.error(f"❌ Failed to get database stats: {e}")
        return {'error': str(e)}

def cleanup_connection_pool():
    """Enhanced cleanup function"""
    global connection_pool
    
    with pool_lock:
        if connection_pool:
            try:
                logger.info("🧹 Cleaning up connection pool...")
                connection_pool.closeall()
                connection_pool = None
                logger.info("✅ Connection pool cleaned up successfully")
            except Exception as e:
                logger.error(f"❌ Error cleaning up connection pool: {e}")
                connection_pool = None

# Initialize connection pool on module import with better error handling
if not connection_pool:
    try:
        logger.info("🚀 Initializing connection pool on module import...")
        init_connection_pool()
    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool on import: {e}")
        # Don't raise here, let the application start and handle it gracefully