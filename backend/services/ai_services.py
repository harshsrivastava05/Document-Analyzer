import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import cohere
import os
import json
from typing import List, Dict, Any
import tempfile
import logging

logger = logging.getLogger(__name__)

class AIServices:
    def __init__(self):
        self.gemini_model = None
        self.pinecone_client = None
        self.cohere_client = None
        self.pinecone_index = None
    
    def initialize(self):
        """Initialize all AI services"""
        try:
            # Initialize Gemini
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set")
            
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("✅ Gemini AI initialized")

            # Initialize Pinecone (new API)
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not pinecone_api_key:
                raise ValueError("PINECONE_API_KEY environment variable is not set")
            
            self.pinecone_client = Pinecone(api_key=pinecone_api_key)
            
            # Get or create index
            index_name = os.getenv("PINECONE_INDEX_NAME", "document-analyzer")
            
            # Check if index exists
            try:
                index_info = self.pinecone_client.describe_index(index_name)
                logger.info(f"✅ Connected to existing Pinecone index: {index_name}")
            except Exception:
                # Index doesn't exist, create it
                logger.info(f"Creating new Pinecone index: {index_name}")
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=1024,  # Cohere embed-multilingual-v3.0 dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'  # Use the free tier region
                    )
                )
                logger.info(f"✅ Created new Pinecone index: {index_name}")
            
            self.pinecone_index = self.pinecone_client.Index(index_name)
            logger.info("✅ Pinecone initialized")

            # Initialize Cohere
            cohere_api_key = os.getenv("COHERE_API_KEY")
            if not cohere_api_key:
                raise ValueError("COHERE_API_KEY environment variable is not set")
            
            self.cohere_client = cohere.Client(cohere_api_key)
            logger.info("✅ Cohere initialized")
            
        except Exception as e:
            logger.error(f"❌ AI services initialization failed: {e}")
            raise
    
    async def analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Gemini AI"""
        temp_file_path = None
        try:
            # Create temporary file for Gemini
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=os.path.splitext(filename)[1]
            ) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Upload file to Gemini
            file = genai.upload_file(
                path=temp_file_path, 
                display_name=os.path.basename(filename)
            )
            
            prompt = """
            Analyze this document and provide:
            1. A comprehensive summary (2-3 paragraphs)
            2. Key topics (5-8 main topics)
            3. Important entities (people, places, organizations, dates)
            4. Overall sentiment (positive, negative, neutral)
            5. Confidence score for the analysis (a float between 0 and 1)

            Format the response as a single, valid JSON object with the following structure:
            {
                "summary": "...",
                "key_topics": ["topic1", "topic2", ...],
                "entities": ["entity1", "entity2", ...],
                "sentiment": "positive/negative/neutral",
                "confidence": 0.95
            }
            """
            
            response = self.gemini_model.generate_content([file, prompt])
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
            result = json.loads(cleaned_text)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            raise
        finally:
            # Cleanup temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not clean up temp file: {cleanup_error}")
    
    def split_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into chunks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > max_chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    async def create_embeddings(self, text_chunks: List[str], document_id: str) -> bool:
        """Create embeddings using Cohere and store in Pinecone"""
        try:
            if not text_chunks:
                logger.warning("No text chunks provided for embedding creation")
                return False
            
            # Create embeddings with Cohere
            response = self.cohere_client.embed(
                texts=text_chunks,
                model="embed-multilingual-v3.0",
                input_type="search_document"
            )
            embeddings = response.embeddings
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
                vector_id = f"{document_id}_{i}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk[:1000]  # Limit text size for metadata
                    }
                })
            
            # Upsert to Pinecone (batch size limit)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.pinecone_index.upsert(vectors=batch)
            
            logger.info(f"✅ Created {len(vectors)} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Embedding creation failed: {e}")
            raise
    
    async def query_rag(self, question: str, document_id: str, k: int = 5) -> Dict[str, Any]:
        """Query RAG pipeline for document-specific answers"""
        try:
            # Create query embedding
            response = self.cohere_client.embed(
                texts=[question],
                model="embed-multilingual-v3.0",
                input_type="search_query"
            )
            query_embedding = response.embeddings[0]
            
            # Search Pinecone
            results = self.pinecone_index.query(
                vector=query_embedding,
                filter={"document_id": {"$eq": document_id}},
                top_k=k,
                include_metadata=True
            )
            
            if not results.matches:
                return {
                    "answer": "I could not find relevant information in the document to answer your question.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Generate answer using retrieved context
            relevant_chunks = [match.metadata["text"] for match in results.matches]
            context = "\n\n".join(relevant_chunks)
            
            prompt = f"""
            Based ONLY on the following context from the document, answer the question.
            Do not use any outside knowledge. If the context doesn't contain the answer, state that clearly.

            Context: {context}

            Question: {question}
            """
            
            response = self.gemini_model.generate_content(prompt)
            
            return {
                "answer": response.text,
                "sources": [match.metadata["chunk_index"] for match in results.matches],
                "confidence": max([match.score for match in results.matches]) if results.matches else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}")
            raise

# Global instance
ai_services = AIServices()

def init_ai_services():
    """Initialize AI services"""
    ai_services.initialize()