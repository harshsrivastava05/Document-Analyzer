# backend/debug_db.py (CREATE THIS FILE)
"""
Database debugging script to test connection issues
Run with: python debug_db.py
"""

import os
import sys
import logging
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def test_direct_connection():
    """Test direct database connection"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL not found in environment variables")
            return False
        
        logger.info(f"🔗 Testing connection to database...")
        logger.info(f"📍 Database URL (masked): {database_url[:20]}...{database_url[-20:]}")
        
        db_config = parse_database_url(database_url)
        logger.info(f"🏠 Host: {db_config['host']}")
        logger.info(f"🔢 Port: {db_config['port']}")
        logger.info(f"📊 Database: {db_config['database']}")
        logger.info(f"👤 User: {db_config['user']}")
        logger.info(f"🔐 SSL Mode: {db_config['sslmode']}")
        
        # Test connection
        connection = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password'],
            sslmode=db_config['sslmode'],
            connect_timeout=30
        )
        
        logger.info("✅ Connection established successfully!")
        
        # Test basic query
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"📋 PostgreSQL version: {version[0]}")
        
        # Test our tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        logger.info(f"📊 Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        # Test user table specifically
        try:
            cursor.execute('SELECT COUNT(*) FROM "users";')
            user_count = cursor.fetchone()[0]
            logger.info(f"👥 Users in database: {user_count}")
        except Exception as e:
            logger.warning(f"⚠️ Could not count users: {e}")
        
        cursor.close()
        connection.close()
        logger.info("✅ Connection test completed successfully!")
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Database connection failed (Operational Error): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Database connection failed (General Error): {e}")
        return False

def test_environment_variables():
    """Test if all required environment variables are set"""
    required_vars = [
        "DATABASE_URL",
        "JWT_SECRET",
        "GEMINI_API_KEY",
        "PINECONE_API_KEY", 
        "COHERE_API_KEY",
        "GCS_BUCKET_NAME",
        "GCS_PROJECT_ID"
    ]
    
    logger.info("🔍 Checking environment variables...")
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values for logging
            if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                masked_value = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
            else:
                masked_value = value
            logger.info(f"✅ {var}: {masked_value}")
        else:
            logger.error(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ All required environment variables are set!")
    return True

def main():
    """Main debugging function"""
    logger.info("🚀 Starting database debugging...")
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test database connection
    db_ok = test_direct_connection()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📋 DEBUGGING SUMMARY:")
    logger.info(f"Environment Variables: {'✅ OK' if env_ok else '❌ ISSUES'}")
    logger.info(f"Database Connection: {'✅ OK' if db_ok else '❌ FAILED'}")
    
    if env_ok and db_ok:
        logger.info("🎉 All tests passed! Your database setup looks good.")
        return 0
    else:
        logger.error("⚠️ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())