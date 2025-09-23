#!/usr/bin/env python3
"""
Health Check & Monitoring Script for AI Document Analyzer
Run this script to check the health of your production deployment
"""

import requests
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HealthChecker:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://localhost:{os.getenv('PORT', 8000)}"
        self.results = {}
        
    def check_api_health(self) -> bool:
        """Check if the API is responding"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.results['api'] = {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'data': data
                }
                return True
            else:
                self.results['api'] = {
                    'status': 'unhealthy',
                    'error': f"HTTP {response.status_code}",
                    'response_time': response.elapsed.total_seconds()
                }
                return False
        except requests.exceptions.RequestException as e:
            self.results['api'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            # Try direct URL connection first
            if os.getenv("DATABASE_URL"):
                connection = psycopg2.connect(
                    os.getenv("DATABASE_URL"),
                    cursor_factory=RealDictCursor,
                    connect_timeout=5
                )
            else:
                # Fallback to individual parameters
                connection = psycopg2.connect(
                    host=os.getenv("NEON_HOST"),
                    database=os.getenv("NEON_DATABASE"),
                    user=os.getenv("NEON_USER"),
                    password=os.getenv("NEON_PASSWORD"),
                    port=int(os.getenv("NEON_PORT", 5432)),
                    sslmode=os.getenv("NEON_SSL_MODE", "require"),
                    cursor_factory=RealDictCursor,
                    connect_timeout=5
                )
            
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Get table counts
            cursor.execute('SELECT COUNT(*) FROM "users"')
            user_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM "documents"')
            doc_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM "qnas"')
            qna_count = cursor.fetchone()[0]
            
            connection.close()
            
            self.results['database'] = {
                'status': 'healthy',
                'users': user_count,
                'documents': doc_count,
                'qnas': qna_count
            }
            return True
            
        except Exception as e:
            self.results['database'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def check_external_apis(self) -> Dict[str, bool]:
        """Check external API connectivity"""
        results = {}
        
        # Check Gemini API
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            # Simple test - this will validate the API key
            model = genai.GenerativeModel('gemini-1.5-flash')
            self.results['gemini'] = {'status': 'configured'}
            results['gemini'] = True
        except Exception as e:
            self.results['gemini'] = {'status': 'error', 'error': str(e)}
            results['gemini'] = False
        
        # Check Pinecone
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index_name = os.getenv("PINECONE_INDEX_NAME")
            if index_name:
                index = pc.Index(index_name)
                stats = index.describe_index_stats()
                self.results['pinecone'] = {
                    'status': 'connected',
                    'vector_count': stats.get('total_vector_count', 0)
                }
                results['pinecone'] = True
            else:
                self.results['pinecone'] = {'status': 'error', 'error': 'Index name not configured'}
                results['pinecone'] = False
        except Exception as e:
            self.results['pinecone'] = {'status': 'error', 'error': str(e)}
            results['pinecone'] = False
        
        # Check Cohere
        try:
            import cohere
            client = cohere.Client(os.getenv("COHERE_API_KEY"))
            # Simple test
            self.results['cohere'] = {'status': 'configured'}
            results['cohere'] = True
        except Exception as e:
            self.results['cohere'] = {'status': 'error', 'error': str(e)}
            results['cohere'] = False
        
        return results
    
    def check_gcs(self) -> bool:
        """Check Google Cloud Storage connectivity"""
        try:
            from google.cloud import storage
            
            project_id = os.getenv("GCS_PROJECT_ID")
            bucket_name = os.getenv("GCS_BUCKET_NAME")
            
            if not project_id or not bucket_name:
                self.results['gcs'] = {
                    'status': 'error',
                    'error': 'GCS project ID or bucket name not configured'
                }
                return False
            
            # Try different authentication methods
            client = None
            auth_method = "default"
            
            if os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64"):
                import base64
                import json
                credentials_json = json.loads(
                    base64.b64decode(os.getenv("GCS_SERVICE_ACCOUNT_KEY_BASE64")).decode('utf-8')
                )
                client = storage.Client.from_service_account_info(credentials_json, project=project_id)
                auth_method = "base64_key"
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                client = storage.Client.from_service_account_json(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), project=project_id
                )
                auth_method = "service_account_file"
            else:
                client = storage.Client(project=project_id)
                auth_method = "default_credentials"
            
            # Test bucket access
            bucket = client.bucket(bucket_name)
            bucket.reload()  # This will raise an exception if bucket doesn't exist or no access
            
            self.results['gcs'] = {
                'status': 'connected',
                'project_id': project_id,
                'bucket_name': bucket_name,
                'auth_method': auth_method
            }
            return True
            
        except Exception as e:
            self.results['gcs'] = {'status': 'error', 'error': str(e)}
            return False
    
    def run_full_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("🔍 Running health checks...")
        print("-" * 50)
        
        # API Health Check
        print("⚡ Checking API health...")
        api_ok = self.check_api_health()
        print(f"   {'✅' if api_ok else '❌'} API: {'Healthy' if api_ok else 'Error'}")
        
        # Database Check
        print("🐘 Checking NeonDB...")
        db_ok = self.check_database()
        print(f"   {'✅' if db_ok else '❌'} Database: {'Connected' if db_ok else 'Error'}")
        
        # External APIs Check
        print("🤖 Checking AI services...")
        api_results = self.check_external_apis()
        for service, ok in api_results.items():
            print(f"   {'✅' if ok else '❌'} {service.capitalize()}: {'Connected' if ok else 'Error'}")
        
        # GCS Check
        print("☁️ Checking Google Cloud Storage...")
        gcs_ok = self.check_gcs()
        print(f"   {'✅' if gcs_ok else '❌'} GCS: {'Connected' if gcs_ok else 'Error'}")
        
        # Overall status
        all_critical_ok = api_ok and db_ok
        all_services_ok = all_critical_ok and all(api_results.values()) and gcs_ok
        
        print("-" * 50)
        if all_services_ok:
            print("✅ All systems operational!")
        elif all_critical_ok:
            print("⚠️ Critical systems operational, some services have issues")
        else:
            print("❌ Critical system failures detected!")
        
        self.results['overall'] = {
            'status': 'healthy' if all_services_ok else 'degraded' if all_critical_ok else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'critical_systems_ok': all_critical_ok,
            'all_systems_ok': all_services_ok
        }
        
        return self.results

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Health check for AI Document Analyzer')
    parser.add_argument('--url', help='Base URL of the API', default=None)
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--continuous', type=int, help='Run continuous monitoring with interval in seconds')
    
    args = parser.parse_args()
    
    checker = HealthChecker(args.url)
    
    if args.continuous:
        print(f"🔄 Starting continuous monitoring (interval: {args.continuous}s)")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                results = checker.run_full_check()
                
                if args.json:
                    print(json.dumps(results, indent=2))
                
                print(f"\n⏰ Next check in {args.continuous} seconds...\n")
                time.sleep(args.continuous)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")
            sys.exit(0)
    else:
        results = checker.run_full_check()
        
        if args.json:
            print("\n📊 Detailed Results:")
            print(json.dumps(results, indent=2))
        
        # Exit with error code if critical systems are down
        if not results['overall']['critical_systems_ok']:
            sys.exit(1)

if __name__ == "__main__":
    main()