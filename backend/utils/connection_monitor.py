# backend/utils/connection_monitor.py - Connection Pool Monitoring
import psycopg2
import logging
import threading
import time
from typing import Dict, Any
from database import connection_pool, pool_lock

logger = logging.getLogger(__name__)

class ConnectionPoolMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get detailed connection pool statistics"""
        if not connection_pool:
            return {"error": "Connection pool not initialized"}
            
        try:
            with pool_lock:
                stats = {
                    "min_connections": connection_pool.minconn,
                    "max_connections": connection_pool.maxconn,
                    "pool_closed": connection_pool.closed,
                    "timestamp": time.time()
                }
                
                # Try to get a connection to test availability
                test_conn = None
                try:
                    start_time = time.time()
                    test_conn = connection_pool.getconn()
                    get_time = time.time() - start_time
                    
                    stats["connection_available"] = True
                    stats["get_connection_time"] = get_time
                    
                    if test_conn:
                        stats["connection_status"] = "healthy" if test_conn.closed == 0 else "closed"
                    
                except Exception as e:
                    stats["connection_available"] = False
                    stats["error"] = str(e)
                    stats["connection_status"] = "error"
                    
                finally:
                    if test_conn:
                        try:
                            connection_pool.putconn(test_conn)
                        except:
                            pass
                
                return stats
                
        except Exception as e:
            return {"error": f"Failed to get pool stats: {e}"}
    
    def log_pool_stats(self):
        """Log current pool statistics"""
        stats = self.get_pool_stats()
        
        if "error" in stats:
            logger.error(f"📊 Pool Monitor Error: {stats['error']}")
        else:
            status_emoji = "✅" if stats.get("connection_available") else "❌"
            logger.info(f"{status_emoji} Pool Stats - Available: {stats.get('connection_available')}, "
                       f"Closed: {stats.get('pool_closed')}, "
                       f"Get Time: {stats.get('get_connection_time', 'N/A'):.3f}s")
    
    def start_monitoring(self, interval: int = 60):
        """Start background monitoring"""
        if self.monitoring:
            logger.warning("Pool monitoring already running")
            return
            
        self.monitoring = True
        
        def monitor_loop():
            logger.info(f"🔍 Started connection pool monitoring (interval: {interval}s)")
            while self.monitoring:
                try:
                    self.log_pool_stats()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Pool monitoring error: {e}")
                    time.sleep(interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.monitoring:
            self.monitoring = False
            logger.info("🛑 Stopped connection pool monitoring")

# Global monitor instance
pool_monitor = ConnectionPoolMonitor()

def check_for_connection_leaks():
    """Check for potential connection leaks"""
    stats = pool_monitor.get_pool_stats()
    
    if stats.get("connection_available") is False:
        logger.error("🚨 POTENTIAL CONNECTION LEAK DETECTED!")
        logger.error("📊 All connections may be in use and not returned to pool")
        logger.error("🔧 Recommended actions:")
        logger.error("   1. Check all database operations use context managers")
        logger.error("   2. Verify connections are properly returned in finally blocks")
        logger.error("   3. Consider restarting the application")
        return True
    
    return False

def emergency_pool_reset():
    """Emergency pool reset (use with caution)"""
    global connection_pool
    
    logger.warning("🚨 EMERGENCY: Attempting to reset connection pool")
    
    try:
        with pool_lock:
            if connection_pool:
                connection_pool.closeall()
                connection_pool = None
                logger.warning("🔄 Pool closed, attempting to reinitialize...")
                
                from database import init_connection_pool
                if init_connection_pool():
                    logger.info("✅ Emergency pool reset successful")
                    return True
                else:
                    logger.error("❌ Emergency pool reset failed")
                    return False
    except Exception as e:
        logger.error(f"❌ Emergency reset error: {e}")
        return False