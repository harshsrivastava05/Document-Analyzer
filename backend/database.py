import mysql.connector
from mysql.connector import Error
import os
from fastapi import HTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes a connection to the MySQL database with connection pooling."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "docanalyzer"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False,
            pool_name="docanalyzer_pool",
            pool_size=10,
            pool_reset_session=True
        )
        return connection
    except Error as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def drop_existing_tables():
    """Drop existing tables to avoid foreign key conflicts."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Disable foreign key checks temporarily
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Drop tables in reverse order of dependencies
        tables_to_drop = ['chat_history', 'documents', 'users']
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"✅ Dropped table {table} if it existed")
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        connection.commit()
        
    except Exception as e:
        logger.error(f"Failed to drop existing tables: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()

def init_db():
    """Initialize database tables with proper schema."""
    connection = None
    try:
        # First drop existing tables to avoid conflicts
        drop_existing_tables()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Create users table first (no foreign keys)
        cursor.execute("""
            CREATE TABLE users (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("✅ Created users table")
        
        # Create documents table (references users)
        cursor.execute("""
            CREATE TABLE documents (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                title VARCHAR(500) NOT NULL,
                gcs_file_id VARCHAR(36) NOT NULL,
                gcs_file_path TEXT,
                mime_type VARCHAR(100),
                file_size BIGINT,
                summary TEXT,
                analysis_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_gcs_file_id (gcs_file_id),
                CONSTRAINT fk_documents_user_id 
                    FOREIGN KEY (user_id) REFERENCES users(id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("✅ Created documents table")
        
        # Create chat_history table (references both users and documents)
        cursor.execute("""
            CREATE TABLE chat_history (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                document_id VARCHAR(36) NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                sources JSON,
                confidence FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_document_user (document_id, user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_user_id (user_id),
                INDEX idx_document_id (document_id),
                CONSTRAINT fk_chat_history_user_id 
                    FOREIGN KEY (user_id) REFERENCES users(id) 
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_chat_history_document_id 
                    FOREIGN KEY (document_id) REFERENCES documents(id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("✅ Created chat_history table")
        
        # Create additional indexes for performance
        cursor.execute("""
            CREATE INDEX idx_chat_history_role_created 
            ON chat_history (role, created_at)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_documents_mime_type 
            ON documents (mime_type)
        """)
        
        connection.commit()
        logger.info("✅ Database tables initialized successfully with proper foreign key constraints")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()

def test_db_connection():
    """Test database connection and basic operations."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            logger.info("✅ Database connection test passed")
            return True
        else:
            logger.error("❌ Database connection test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            connection.close()

def get_db_stats():
    """Get database statistics for monitoring."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        stats = {}
        
        # Get table counts
        tables = ['users', 'documents', 'chat_history']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[f"{table}_count"] = count
        
        # Get database size
        cursor.execute("""
            SELECT 
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'db_size_mb'
            FROM information_schema.tables 
            WHERE table_schema = %s
        """, (os.getenv("MYSQL_DATABASE", "docanalyzer"),))
        
        result = cursor.fetchone()
        stats['database_size_mb'] = result[0] if result and result[0] else 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}
    finally:
        if connection and connection.is_connected():
            connection.close()