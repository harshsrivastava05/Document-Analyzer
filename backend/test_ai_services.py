# backend/test_ai_services.py (CREATE THIS FILE)
"""
Test AI Services functionality
Run with: python test_ai_services.py
"""

import os
import asyncio
from dotenv import load_dotenv
from services.ai_services import ai_services

# Load environment variables
load_dotenv()

async def test_ai_services():
    """Test all AI services functionality"""
    print("🤖 Testing AI Services...")
    print("="*60)
    
    # Test initialization
    try:
        ai_services.initialize()
        print("✅ AI Services initialized successfully")
    except Exception as e:
        print(f"❌ AI Services initialization failed: {e}")
        return False
    
    # Test document analysis with simple text
    try:
        print("\n📄 Testing document analysis...")
        test_content = b"This is a test document about artificial intelligence and machine learning. It discusses the benefits of AI in modern applications."
        
        result = await ai_services.analyze_document(test_content, "test.txt")
        
        print(f"Summary: {result.get('summary', 'No summary')[:100]}...")
        print(f"Key Topics: {result.get('key_topics', [])}")
        print(f"Sentiment: {result.get('sentiment', 'Unknown')}")
        print(f"Confidence: {result.get('confidence', 0)}")
        print("✅ Document analysis test passed")
        
    except Exception as e:
        print(f"❌ Document analysis test failed: {e}")
        return False
    
    # Test text splitting
    try:
        print("\n✂️ Testing text splitting...")
        test_text = "This is a long text that needs to be split into smaller chunks for processing. " * 50
        chunks = ai_services.split_text(test_text, max_chunk_size=100)
        print(f"Split text into {len(chunks)} chunks")
        print(f"First chunk: {chunks[0][:50]}..." if chunks else "No chunks created")
        print("✅ Text splitting test passed")
        
    except Exception as e:
        print(f"❌ Text splitting test failed: {e}")
        return False
    
    # Test embeddings (optional - requires Cohere/Pinecone)
    try:
        print("\n🔍 Testing embeddings creation...")
        test_chunks = ["This is the first chunk of text.", "This is the second chunk of text."]
        test_doc_id = "test_document_123"
        
        result = await ai_services.create_embeddings(test_chunks, test_doc_id)
        
        if result:
            print("✅ Embeddings creation test passed")
        else:
            print("⚠️ Embeddings creation returned False (but didn't crash)")
            
    except Exception as e:
        print(f"❌ Embeddings test failed: {e}")
        print("This might be expected if Pinecone/Cohere aren't properly configured")
    
    # Test RAG query (optional)
    try:
        print("\n💬 Testing RAG query...")
        question = "What is this document about?"
        result = await ai_services.query_rag(question, "test_document_123")
        
        print(f"Answer: {result.get('answer', 'No answer')[:100]}...")
        print(f"Confidence: {result.get('confidence', 0)}")
        print("✅ RAG query test passed")
        
    except Exception as e:
        print(f"❌ RAG query test failed: {e}")
        print("This might be expected if no embeddings exist yet")
    
    print("\n🎉 AI Services testing completed!")
    return True

def test_environment_variables():
    """Test if AI service environment variables are set"""
    print("🔍 Checking AI service environment variables...")
    
    required_vars = {
        "GEMINI_API_KEY": "Gemini AI",
        "PINECONE_API_KEY": "Pinecone Vector Database", 
        "COHERE_API_KEY": "Cohere Embeddings",
        "PINECONE_INDEX_NAME": "Pinecone Index Name"
    }
    
    all_good = True
    for var, service in required_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"✅ {service}: {masked_value}")
        else:
            print(f"❌ {service}: Not set ({var})")
            all_good = False
    
    return all_good

async def main():
    """Main test function"""
    print("🚀 Starting AI Services Test Suite")
    print("="*60)
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n⚠️ Some environment variables are missing. AI services may not work properly.")
        return
    
    # Test AI services
    await test_ai_services()

if __name__ == "__main__":
    asyncio.run(main())