# backend/services/ai_services.py
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import cohere
import os
import json
from typing import List, Dict, Any, Optional
import logging
import PyPDF2
import docx
import io

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
            
            # Model priority list - try from newest to oldest
            model_names = [
                'gemini-2.0-flash-exp',       # Latest experimental
                'gemini-1.5-flash',           # Stable and fast
                'gemini-1.5-pro',             # More capable but slower
                'gemini-pro'                  # Legacy fallback
            ]
            
            self.gemini_model = None
            for model_name in model_names:
                try:
                    self.gemini_model = genai.GenerativeModel(model_name)
                    # Test the model with a simple request
                    test_response = self.gemini_model.generate_content(
                        "Hello", 
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=50
                        )
                    )
                    if test_response and test_response.text:
                        logger.info(f"✅ Gemini AI initialized with model: {model_name}")
                        break
                except Exception as model_error:
                    logger.warning(f"Failed to initialize model {model_name}: {model_error}")
                    continue
            
            if not self.gemini_model:
                raise ValueError("Could not initialize any Gemini model. Please check your API key.")

            # Initialize Pinecone
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not pinecone_api_key:
                logger.warning("PINECONE_API_KEY not set - RAG features will be disabled")
                self.pinecone_index = None
            else:
                try:
                    self.pinecone_client = Pinecone(api_key=pinecone_api_key)
                    index_name = os.getenv("PINECONE_INDEX_NAME", "document-analyzer")
                    
                    # Check if index exists, create if not
                    try:
                        self.pinecone_client.describe_index(index_name)
                        logger.info(f"✅ Connected to existing Pinecone index: {index_name}")
                    except Exception:
                        logger.info(f"Creating new Pinecone index: {index_name}")
                        self.pinecone_client.create_index(
                            name=index_name,
                            dimension=1024,  # Cohere embed-multilingual-v3.0 dimension
                            metric='cosine',
                            spec=ServerlessSpec(cloud='aws', region='us-east-1')
                        )
                        logger.info(f"✅ Created new Pinecone index: {index_name}")
                    
                    self.pinecone_index = self.pinecone_client.Index(index_name)
                    logger.info("✅ Pinecone initialized")
                    
                except Exception as pinecone_error:
                    logger.warning(f"Pinecone initialization failed: {pinecone_error}")
                    self.pinecone_index = None

            # Initialize Cohere
            cohere_api_key = os.getenv("COHERE_API_KEY")
            if not cohere_api_key:
                logger.warning("COHERE_API_KEY not set - embedding features will be disabled")
                self.cohere_client = None
            else:
                try:
                    self.cohere_client = cohere.Client(cohere_api_key)
                    logger.info("✅ Cohere initialized")
                except Exception as cohere_error:
                    logger.warning(f"Cohere initialization failed: {cohere_error}")
                    self.cohere_client = None
            
        except Exception as e:
            logger.error(f"❌ AI services initialization failed: {e}")
            raise
    
    def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file types"""
        try:
            file_extension = os.path.splitext(filename.lower())[1]
            
            if file_extension == '.pdf':
                return self._extract_text_from_pdf(file_content)
            elif file_extension in ['.docx', '.doc']:
                return self._extract_text_from_docx(file_content)
            elif file_extension == '.txt':
                return file_content.decode('utf-8', errors='ignore')
            else:
                # Fallback: try to decode as text
                return file_content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.warning(f"Text extraction failed for {filename}: {e}")
            # Fallback: try to decode as plain text
            try:
                return file_content.decode('utf-8', errors='ignore')
            except:
                return f"[Could not extract text from {filename}]"
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF using PyPDF2"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            raise
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX files"""
        try:
            doc = docx.Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.warning(f"DOCX text extraction failed: {e}")
            raise
    
    async def analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Gemini AI"""
        try:
            if not self.gemini_model:
                return {
                    "summary": "AI analysis not available - Gemini not initialized",
                    "key_topics": [],
                    "entities": [],
                    "sentiment": "neutral",
                    "confidence": 0.0
                }

            # Extract text from the document
            text_content = self.extract_text_from_file(file_content, filename)
            
            if not text_content.strip():
                return {
                    "summary": "Could not extract text from document",
                    "key_topics": [],
                    "entities": [],
                    "sentiment": "neutral",
                    "confidence": 0.0
                }
            
            # Limit text length for API call
            max_text_length = 30000  # Conservative limit
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length] + "...[truncated]"
            
            # Create analysis prompt
            prompt = f"""
            Analyze this document and provide insights in JSON format.

            Document: {filename}
            Text Content:
            {text_content}

            Respond ONLY with valid JSON in this format:
            {{
                "summary": "2-3 sentence summary of the document's main content",
                "key_topics": ["topic1", "topic2", "topic3"],
                "entities": ["entity1", "entity2", "entity3"],
                "sentiment": "positive/negative/neutral",
                "confidence": 0.85,
                "document_type": "report/article/letter/etc",
                "insights": ["insight1", "insight2", "insight3"]
            }}

            Focus on accuracy and extract the most important information.
            """
            
            # Generate analysis
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1500,
                candidate_count=1
            )
            
            response = self.gemini_model.generate_content(
                prompt, 
                generation_config=generation_config
            )
            
            if not response or not response.text:
                raise Exception("No response from Gemini API")

            # Clean and parse response
            cleaned_text = response.text.strip()
            
            # Remove markdown formatting if present
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            try:
                result = json.loads(cleaned_text)
                
                # Validate and set defaults
                result.setdefault("summary", f"Analysis completed for {filename}")
                result.setdefault("key_topics", [])
                result.setdefault("entities", [])
                result.setdefault("sentiment", "neutral")
                result.setdefault("confidence", 0.7)
                result.setdefault("document_type", "document")
                result.setdefault("insights", [])
                
                logger.info(f"✅ Document analysis completed for {filename}")
                return result
                
            except json.JSONDecodeError as json_error:
                logger.warning(f"JSON parsing failed: {json_error}")
                logger.debug(f"Raw response: {cleaned_text[:200]}...")
                
                # Fallback response
                return {
                    "summary": f"Analysis completed for {filename}. Document contains {len(text_content.split())} words.",
                    "key_topics": ["document analysis", "text processing"],
                    "entities": [],
                    "sentiment": "neutral", 
                    "confidence": 0.6,
                    "document_type": "document",
                    "insights": [
                        f"Document processed successfully",
                        f"Text extraction completed",
                        "Ready for question answering"
                    ]
                }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed for {filename}: {e}")
            return {
                "summary": f"Analysis failed for {filename}: {str(e)[:100]}",
                "key_topics": ["error"],
                "entities": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "document_type": "unknown",
                "insights": ["Processing failed - manual review needed"]
            }
    
    def split_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        if not text.strip():
            return []
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                if overlap > 0:
                    overlap_words = min(overlap, len(current_chunk) // 2)
                    current_chunk = current_chunk[-overlap_words:] + [word]
                    current_size = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk = [word]
                    current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        logger.info(f"✅ Split text into {len(chunks)} chunks")
        return chunks
    
    async def create_embeddings(self, text_chunks: List[str], document_id: str) -> bool:
        """Create embeddings using Cohere and store in Pinecone"""
        try:
            if not self.cohere_client or not self.pinecone_index:
                logger.warning("Embeddings not available - Cohere or Pinecone not initialized")
                return False
                
            if not text_chunks:
                logger.warning("No text chunks provided")
                return False
            
            # Filter out empty chunks
            valid_chunks = [chunk.strip() for chunk in text_chunks if chunk.strip()]
            if not valid_chunks:
                logger.warning("No valid text chunks after filtering")
                return False
            
            # Create embeddings with Cohere
            try:
                response = self.cohere_client.embed(
                    texts=valid_chunks,
                    model="embed-multilingual-v3.0",
                    input_type="search_document"
                )
            except Exception:
                # Fallback without input_type
                response = self.cohere_client.embed(
                    texts=valid_chunks,
                    model="embed-multilingual-v3.0"
                )
            
            embeddings = response.embeddings
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(valid_chunks, embeddings)):
                vector_id = f"{document_id}_{i}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk[:800]  # Limit metadata size
                    }
                })
            
            # Upsert to Pinecone in batches
            batch_size = 50
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.pinecone_index.upsert(vectors=batch)
            
            logger.info(f"✅ Created {len(vectors)} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Embedding creation failed: {e}")
            return False
    
    async def query_rag(self, question: str, document_id: str, k: int = 5) -> Dict[str, Any]:
        """Query RAG pipeline for document-specific answers"""
        try:
            if not self.cohere_client or not self.pinecone_index or not self.gemini_model:
                return {
                    "answer": "RAG functionality is not available - required services not initialized.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Create query embedding
            try:
                response = self.cohere_client.embed(
                    texts=[question],
                    model="embed-multilingual-v3.0",
                    input_type="search_query"
                )
            except Exception:
                # Fallback without input_type
                response = self.cohere_client.embed(
                    texts=[question],
                    model="embed-multilingual-v3.0"
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
            Based on the following context from the document, answer the question.

            CONTEXT:
            {context}

            QUESTION: {question}

            INSTRUCTIONS:
            - Answer based ONLY on the provided context
            - If the context doesn't contain enough information, say so
            - Be specific and concise
            - If uncertain, indicate your confidence level

            ANSWER:
            """
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=800
            )
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if not response or not response.text:
                raise Exception("No response from Gemini for RAG query")
            
            # Calculate confidence based on match scores
            avg_confidence = sum(match.score for match in results.matches) / len(results.matches)
            
            return {
                "answer": response.text.strip(),
                "sources": [match.metadata["chunk_index"] for match in results.matches],
                "confidence": min(avg_confidence, 1.0),
                "chunks_used": len(results.matches)
            }
            
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}")
            return {
                "answer": f"I encountered an error while searching the document: {str(e)[:100]}",
                "sources": [],
                "confidence": 0.0
            }

# Global instance
ai_services = AIServices()

def init_ai_services():
    """Initialize AI services"""
    try:
        ai_services.initialize()
        logger.info("✅ AI Services initialization completed")
    except Exception as e:
        logger.error(f"❌ AI Services initialization failed: {e}")
        logger.warning("Application will continue with limited AI functionality")
        # Don't raise - let the app continue