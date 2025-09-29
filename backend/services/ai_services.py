# backend/services/ai_services.py (UPDATED VERSION)
import google.generativeai as genai #type:ignore
from pinecone import Pinecone, ServerlessSpec #type:ignore
import cohere #type:ignore
import os
import json
from typing import List, Dict, Any
import tempfile
import logging
import PyPDF2
try:
    # Fallback PDF extraction if PyPDF2 returns little or no text
    from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
    PDFMINER_AVAILABLE = True
except Exception:
    PDFMINER_AVAILABLE = False
import io
from docx import Document as DocxDocument

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
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
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
    
    def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file types"""
        try:
            file_extension = os.path.splitext(filename.lower())[1]
            
            if file_extension == '.txt':
                # Plain text file
                return file_content.decode('utf-8', errors='ignore')
            
            elif file_extension == '.pdf':
                # PDF file
                try:
                    pdf_file = io.BytesIO(file_content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in pdf_reader.pages:
                        try:
                            page_text = page.extract_text() or ""
                        except Exception:
                            page_text = ""
                        text += page_text + "\n"
                    # If PyPDF2 couldn't extract much, try pdfminer as a fallback
                    if PDFMINER_AVAILABLE and len(text.strip()) < 50:
                        try:
                            tmp = io.BytesIO(file_content)
                            text = pdfminer_extract_text(tmp)
                        except Exception as e2:
                            logger.warning(f"pdfminer fallback failed: {e2}")
                    return text
                except Exception as e:
                    logger.warning(f"Failed to extract PDF text: {e}")
                    # Try pdfminer as a last resort
                    if PDFMINER_AVAILABLE:
                        try:
                            tmp = io.BytesIO(file_content)
                            return pdfminer_extract_text(tmp)
                        except Exception as e2:
                            logger.warning(f"pdfminer last-resort failed: {e2}")
                    return ""
            
            elif file_extension in ['.docx']:
                # DOCX file
                try:
                    doc_file = io.BytesIO(file_content)
                    doc = DocxDocument(doc_file)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except Exception as e:
                    logger.warning(f"Failed to extract DOCX text: {e}")
                    return ""
            
            else:
                # Try to decode as text
                try:
                    return file_content.decode('utf-8', errors='ignore')
                except:
                    logger.warning(f"Could not extract text from {filename}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    async def analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Gemini AI with text-only input"""
        try:
            # Extract text from file
            text_content = self.extract_text_from_file(file_content, filename)
            
            if not text_content.strip():
                return {
                    "summary": f"Document uploaded: {filename}. Text extraction not available for this file type.",
                    "key_topics": ["document", "upload"],
                    "entities": [filename],
                    "sentiment": "neutral",
                    "confidence": 0.5
                }
            
            # Limit text length for API (Gemini has token limits)
            max_text_length = 30000  # Approximately 7500 tokens
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length] + "\n\n[Text truncated...]"
            
            prompt = f"""
            Analyze the following document text and provide:
            1. A comprehensive summary (2-3 paragraphs)
            2. Key topics (5-8 main topics)
            3. Important entities (people, places, organizations, dates)
            4. Overall sentiment (positive, negative, neutral)
            5. Confidence score for the analysis (a float between 0 and 1)

            Document text:
            {text_content}

            Format the response as a single, valid JSON object with the following structure:
            {{
                "summary": "...",
                "key_topics": ["topic1", "topic2", ...],
                "entities": ["entity1", "entity2", ...],
                "sentiment": "positive/negative/neutral",
                "confidence": 0.95
            }}
            """
            
            response = self.gemini_model.generate_content(prompt)
            
            # Clean up the response text
            response_text = response.text.strip()
            
            # Remove markdown code block markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                
                # Fallback response
                return {
                    "summary": f"Document '{filename}' has been analyzed. The document contains {len(text_content.split())} words and appears to be about {filename.split('.')[0]}.",
                    "key_topics": ["document", "analysis"],
                    "entities": [filename],
                    "sentiment": "neutral",
                    "confidence": 0.7
                }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            
            # Return a fallback response instead of raising
            return {
                "summary": f"Document '{filename}' was uploaded successfully. Analysis encountered an issue: {str(e)[:100]}",
                "key_topics": ["document", "upload"],
                "entities": [filename],
                "sentiment": "neutral",
                "confidence": 0.3
            }
    
    def split_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into chunks"""
        if not text or not text.strip():
            return []
            
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > max_chunk_size:
                if current_chunk:  # Only add non-empty chunks
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
            
            # Filter out empty chunks
            text_chunks = [chunk.strip() for chunk in text_chunks if chunk.strip()]
            
            if not text_chunks:
                logger.warning("No non-empty text chunks found")
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
            # Don't raise, just return False so document still gets saved
            return False
    
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
            return {
                "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }

# Global instance
ai_services = AIServices()

def init_ai_services():
    """Initialize AI services"""
    ai_services.initialize()