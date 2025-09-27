import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import cohere
import os
import json
from typing import List, Dict, Any, Optional
import tempfile
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
            
            # List available models for debugging
            try:
                available_models = genai.list_models()
                logger.info("Available Gemini models:")
                for model in available_models:
                    if hasattr(model, 'name'):
                        logger.info(f"  - {model.name}")
            except Exception as list_error:
                logger.warning(f"Could not list available models: {list_error}")
            
            # Try different model names based on API version
            model_names = [
                'gemini-1.5-flash',
                'gemini-pro',
                'models/gemini-pro',
                'models/gemini-1.5-flash',
                'gemini-1.5-pro'
            ]
            
            self.gemini_model = None
            for model_name in model_names:
                try:
                    self.gemini_model = genai.GenerativeModel(model_name)
                    # Test the model with a simple request
                    test_response = self.gemini_model.generate_content("Test")
                    logger.info(f"✅ Gemini AI initialized with model: {model_name}")
                    break
                except Exception as model_error:
                    logger.warning(f"Failed to initialize model {model_name}: {model_error}")
                    continue
            
            if not self.gemini_model:
                raise ValueError("Could not initialize any Gemini model. Please check your API key and available models.")

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
                try:
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
                except Exception as create_error:
                    logger.warning(f"Failed to create Pinecone index: {create_error}")
                    logger.warning("Continuing without Pinecone - RAG features will be disabled")
            
            try:
                self.pinecone_index = self.pinecone_client.Index(index_name)
                logger.info("✅ Pinecone initialized")
            except Exception as pinecone_error:
                logger.warning(f"Pinecone connection failed: {pinecone_error}")
                logger.warning("Continuing without Pinecone - RAG features will be disabled")
                self.pinecone_index = None

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
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            raise
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX files"""
        try:
            doc = docx.Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.warning(f"DOCX text extraction failed: {e}")
            raise
    
    async def analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Gemini AI with text-based approach"""
        try:
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
            
            # Limit text length for API call (Gemini has input limits)
            max_text_length = 30000  # Adjust based on model limits
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length] + "...[truncated]"
            
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

            Ensure the response is valid JSON with no additional text before or after.
            """
            
            response = self.gemini_model.generate_content(prompt)
            
            # Clean the response text
            cleaned_text = response.text.strip()
            
            # Remove common markdown formatting
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            try:
                result = json.loads(cleaned_text)
                logger.info(f"✅ Document analysis completed for {filename}")
                return result
            except json.JSONDecodeError as json_error:
                logger.warning(f"JSON parsing failed, using fallback response: {json_error}")
                # Fallback response
                return {
                    "summary": f"Analysis completed for {filename}. The document contains {len(text_content)} characters of text.",
                    "key_topics": ["document analysis", "content extraction"],
                    "entities": [],
                    "sentiment": "neutral",
                    "confidence": 0.5
                }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed for {filename}: {e}")
            # Return a safe fallback instead of raising
            return {
                "summary": f"Analysis failed for {filename}: {str(e)[:200]}",
                "key_topics": ["error", "analysis failed"],
                "entities": [],
                "sentiment": "neutral",
                "confidence": 0.0
            }
    
    def split_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        if not text.strip():
            return []
        
        # Split by sentences first, then by chunks
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add period back if it's not the last sentence
            if not sentence.endswith('.') and not sentence.endswith('!') and not sentence.endswith('?'):
                sentence += '.'
            
            sentence_size = len(sentence) + 1  # +1 for space
            
            if current_size + sentence_size > max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                if overlap > 0 and len(current_chunk) > 1:
                    overlap_sentences = current_chunk[-2:]  # Keep last 2 sentences for overlap
                    current_chunk = overlap_sentences + [sentence]
                    current_size = sum(len(s) + 1 for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    async def create_embeddings(self, text_chunks: List[str], document_id: str) -> bool:
        """Create embeddings using Cohere and store in Pinecone"""
        try:
            if not text_chunks:
                logger.warning("No text chunks provided for embedding creation")
                return False
            
            if not self.pinecone_index:
                logger.warning("Pinecone not available, skipping embedding creation")
                return False
            
            # Filter out empty chunks
            valid_chunks = [chunk for chunk in text_chunks if chunk.strip()]
            if not valid_chunks:
                logger.warning("No valid text chunks after filtering")
                return False
            
            # Create embeddings with Cohere (try different API versions)
            try:
                # Try newer API first
                response = self.cohere_client.embed(
                    texts=valid_chunks,
                    model="embed-multilingual-v3.0",
                    input_type="search_document"
                )
            except Exception as api_error:
                logger.warning(f"New Cohere API failed, trying legacy API: {api_error}")
                try:
                    # Fallback to older API without input_type
                    response = self.cohere_client.embed(
                        texts=valid_chunks,
                        model="embed-multilingual-v3.0"
                    )
                except Exception as legacy_error:
                    logger.warning(f"Legacy Cohere API failed, trying basic embed: {legacy_error}")
                    # Try even simpler API call
                    response = self.cohere_client.embed(
                        texts=valid_chunks
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
            logger.warning("Continuing without embeddings - RAG features may be limited")
            return False
    
    async def query_rag(self, question: str, document_id: str, k: int = 5) -> Dict[str, Any]:
        """Query RAG pipeline for document-specific answers"""
        try:
            if not self.pinecone_index:
                return {
                    "answer": "RAG functionality is not available - Pinecone connection failed.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Create query embedding (with API version handling)
            try:
                response = self.cohere_client.embed(
                    texts=[question],
                    model="embed-multilingual-v3.0",
                    input_type="search_query"
                )
            except Exception:
                try:
                    # Fallback without input_type
                    response = self.cohere_client.embed(
                        texts=[question],
                        model="embed-multilingual-v3.0"
                    )
                except Exception:
                    # Basic fallback
                    response = self.cohere_client.embed(
                        texts=[question]
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

            Answer:
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
                "answer": f"Sorry, I encountered an error while searching the document: {str(e)}",
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