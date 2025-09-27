# backend/services/ai_services.py
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
            
            # Updated model priority list with latest models
            model_names = [
                'gemini-2.5-flash',           # Latest and best performance
                'models/gemini-2.5-flash',
                'gemini-2.0-flash-exp',       # Experimental Gemini 2.0 Flash
                'models/gemini-2.0-flash-exp',
                'gemini-1.5-flash',           # Fallback to 1.5 Flash
                'gemini-pro',                 # Legacy fallback
                'models/gemini-pro',
                'models/gemini-1.5-flash',
                'gemini-1.5-pro'              # Last resort
            ]
            
            self.gemini_model = None
            for model_name in model_names:
                try:
                    self.gemini_model = genai.GenerativeModel(model_name)
                    # Test the model with a simple request
                    test_response = self.gemini_model.generate_content("Test", 
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.7,
                            max_output_tokens=100
                        ))
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
        """Analyze document using Gemini AI with enhanced prompting for 2.5 Flash"""
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
            
            # Limit text length for API call (Gemini 2.5 Flash has higher limits but be safe)
            max_text_length = 50000  # Increased for Gemini 2.5 Flash
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length] + "...[truncated]"
            
            # Enhanced prompt for Gemini 2.5 Flash with thinking capabilities
            prompt = f"""
            You are an expert document analyst. Analyze the following document text comprehensively and provide detailed insights.

            Document: {filename}
            Text Content:
            {text_content}

            Please provide your analysis in the following JSON format (respond ONLY with valid JSON):
            {{
                "summary": "A comprehensive 3-4 sentence summary of the document's main content and purpose",
                "key_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
                "entities": ["person1", "organization1", "location1", "date1", "important_concept1"],
                "sentiment": "positive/negative/neutral/mixed",
                "confidence": 0.95,
                "document_type": "report/article/manual/letter/etc",
                "word_count": {len(text_content.split())},
                "insights": [
                    "Key insight 1 about the document",
                    "Key insight 2 about the document", 
                    "Key insight 3 about the document"
                ]
            }}

            Guidelines:
            - Focus on the most important and relevant information
            - Extract specific entities (names, places, organizations, dates)
            - Determine the overall sentiment and tone
            - Provide actionable insights about the content
            - Be concise but comprehensive
            - Confidence should reflect how certain you are about your analysis (0.0 to 1.0)
            """
            
            # Use improved generation config for Gemini 2.5 Flash
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_output_tokens=2000,  # Increased output tokens
                candidate_count=1,
                top_p=0.9,
                top_k=40
            )
            
            response = self.gemini_model.generate_content(
                prompt, 
                generation_config=generation_config
            )
            
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
                
                # Validate required fields and provide defaults
                result.setdefault("summary", f"Analysis completed for {filename}")
                result.setdefault("key_topics", [])
                result.setdefault("entities", [])
                result.setdefault("sentiment", "neutral")
                result.setdefault("confidence", 0.8)
                result.setdefault("document_type", "document")
                result.setdefault("insights", [])
                
                logger.info(f"✅ Enhanced document analysis completed for {filename} using Gemini 2.5 Flash")
                return result
                
            except json.JSONDecodeError as json_error:
                logger.warning(f"JSON parsing failed, using fallback response: {json_error}")
                logger.warning(f"Raw response: {cleaned_text[:500]}...")
                # Enhanced fallback response
                return {
                    "summary": f"Advanced analysis completed for {filename}. The document contains {len(text_content)} characters of text across {len(text_content.split())} words.",
                    "key_topics": ["document analysis", "content extraction", "automated processing"],
                    "entities": [],
                    "sentiment": "neutral", 
                    "confidence": 0.6,
                    "document_type": "document",
                    "insights": [
                        f"Document processed with Gemini 2.5 Flash",
                        f"Text extraction successful from {filename}",
                        "Ready for RAG-based question answering"
                    ]
                }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed for {filename}: {e}")
            # Return a safe fallback instead of raising
            return {
                "summary": f"Analysis encountered an error for {filename}: {str(e)[:200]}",
                "key_topics": ["error", "analysis failed"],
                "entities": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "document_type": "unknown",
                "insights": ["Processing failed - document may need manual review"]
            }
    
    def split_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks with improved strategy for Gemini 2.5 Flash"""
        if not text.strip():
            return []
        
        # Enhanced chunking for better embeddings
        # Split by paragraphs first, then sentences, then chunks
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            sentences = paragraph.replace('\n', ' ').split('. ')
            
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
                    if overlap > 0 and len(current_chunk) > 2:
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
        
        logger.info(f"✅ Split text into {len(chunks)} chunks for better RAG performance")
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
        """Query RAG pipeline for document-specific answers using Gemini 2.5 Flash"""
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
            
            # Generate answer using retrieved context with enhanced prompt for Gemini 2.5 Flash
            relevant_chunks = [match.metadata["text"] for match in results.matches]
            context = "\n\n".join(relevant_chunks)
            
            # Enhanced prompt for Gemini 2.5 Flash's reasoning capabilities
            prompt = f"""
            You are an expert document analyst with access to specific document content. 
            
            CONTEXT FROM DOCUMENT:
            {context}

            QUESTION: {question}

            INSTRUCTIONS:
            - Answer the question based ONLY on the provided context
            - If the context doesn't contain enough information, state that clearly
            - Be specific and cite relevant parts of the context
            - Provide a comprehensive but concise answer
            - If you're uncertain about something, indicate your confidence level

            ANSWER:
            """
            
            # Use optimized generation config for RAG responses
            generation_config = genai.types.GenerationConfig(
                temperature=0.2,  # Lower temperature for more factual responses
                max_output_tokens=1000,
                top_p=0.8,
                top_k=20
            )
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Calculate confidence based on match scores
            avg_confidence = sum([match.score for match in results.matches]) / len(results.matches)
            
            return {
                "answer": response.text,
                "sources": [match.metadata["chunk_index"] for match in results.matches],
                "confidence": min(avg_confidence, 1.0),
                "chunks_used": len(results.matches)
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
        logger.info("✅ AI Services initialization completed with Gemini 2.5 Flash")
    except Exception as e:
        logger.error(f"❌ AI Services initialization failed: {e}")
        logger.warning("Application will continue with limited AI functionality")
        # Don't raise - let the app continue