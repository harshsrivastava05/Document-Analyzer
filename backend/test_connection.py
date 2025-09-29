# Create backend/test_connection.py
import os
import socket
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def test_dns_resolution(hostname):
    """Test if we can resolve the hostname"""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS Resolution successful: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS Resolution failed: {hostname} -> {e}")
        return False

def test_port_connectivity(hostname, port=5432):
    """Test if we can connect to the port"""
    try:
        sock = socket.create_connection((hostname, port), timeout=10)
        sock.close()
        print(f"✅ Port connectivity successful: {hostname}:{port}")
        return True
    except (socket.timeout, ConnectionRefusedError, socket.gaierror) as e:
        print(f"❌ Port connectivity failed: {hostname}:{port} -> {e}")
        return False

def test_database_connection():
    """Test the actual database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    print(f"🔍 Testing DATABASE_URL: {database_url}")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        port = parsed.port or 5432
        database = parsed.path[1:]  # Remove leading '/'
        username = parsed.username
        password = parsed.password
        
        print(f"📋 Connection details:")
        print(f"   Host: {hostname}")
        print(f"   Port: {port}")
        print(f"   Database: {database}")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password) if password else 'None'}")
        
        # Test DNS resolution first
        if not test_dns_resolution(hostname):
            return False
        
        # Test port connectivity
        if not test_port_connectivity(hostname, port):
            return False
        
        # Test actual database connection
        print(f"🔌 Testing database connection...")
        conn = psycopg2.connect(
            host=hostname,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='require',
            connect_timeout=30
        )
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result[0] == 1:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database query failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes"""
    print("\n🔧 Potential fixes:")
    print("1. Check if your Neon database is active (not suspended)")
    print("2. Verify your DATABASE_URL is correct")
    print("3. Check your internet connection")
    print("4. Try using a different DNS server (8.8.8.8, 1.1.1.1)")
    print("5. Check if your firewall is blocking connections")
    print("6. Try connecting from a different network")
    print("7. Check Neon dashboard for database status")

if __name__ == "__main__":
    print("🧪 Testing database connectivity...")
    print("=" * 50)
    
    success = test_database_connection()
    
    if not success:
        suggest_fixes()
    
    print("=" * 50)
    print("Test completed.")