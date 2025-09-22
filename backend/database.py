import mysql.connector
from mysql.connector import Error
import os
from fastapi import HTTPException

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        return connection
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def init_db():
    """Initialize database tables if they don't exist."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Create users table (with password_hash field)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                password_hash VARCHAR(255) NOT NULL,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                gcs_file_id VARCHAR(36) NOT NULL,
                gcs_file_path TEXT,
                mime_type VARCHAR(100),
                file_size BIGINT,
                summary TEXT,
                analysis_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at)
            )
        """)
        
        # Create chat_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                document_id VARCHAR(36) NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                sources JSON,
                confidence FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                INDEX idx_document_user (document_id, user_id),
                INDEX idx_created_at (created_at)
            )
        """)
        
        connection.commit()
        print("✅ Database tables initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()