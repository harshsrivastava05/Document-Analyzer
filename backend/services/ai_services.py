# services/ai_services.py
from services.ai.gemini_service import GeminiService
from services.embeddings.cohere_service import CohereService
from services.vectorstore.pinecone_service import PineconeService
import PyPDF2
from docx import Document
import logging
from typing import List, Dict, Any
import io

logger = logging.getLogger(__name__)

class AIServices:
    def __init__(self):
        self.gemini = GeminiService()
        self.cohere = CohereService()
        self.pinecone = PineconeService()

    def initialize(self):
        self.gemini.initialize()
        self.cohere.initialize()
        self.pinecone.initialize()

    async def analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze document using Gemini"""
        try:
            if not self.gemini.model:
                return {"summary": "AI service not available"}
            
            # Extract text first
            text = self.extract_text_from_file(file_content, filename)
            
            if not text:
                return {"summary": "Could not extract text from document"}
            
            # Generate analysis with Gemini
            prompt = f"""Analyze the following document and provide:
            1. A brief summary (2-3 sentences)
            2. Key topics
            3. Important entities mentioned
            
            Document text:
            {text[:5000]}  # Limit text to avoid token limits
            
            Provide response in JSON format with keys: summary, key_topics, entities
            """
            
            response = self.gemini.model.generate_content(prompt)
            
            # Parse response and return structured data
            import json
            try:
                result = json.loads(response.text)
                return result
            except:
                # Fallback if JSON parsing fails
                return {
                    "summary": response.text[:500] if response.text else "Analysis completed",
                    "key_topics": [],
                    "entities": []
                }
                
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {"summary": f"Analysis failed: {str(e)[:200]}"}

    def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            if file_ext == 'pdf':
                return self._extract_from_pdf(file_content)
            elif file_ext in ['doc', 'docx']:
                return self._extract_from_docx(file_content)
            elif file_ext == 'txt':
                return file_content.decode('utf-8', errors='ignore')
            else:
                # Try as text
                return file_content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ""
    
    def split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into chunks for embedding"""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk.rfind('.')
                if last_period > chunk_size * 0.5:  # Only if we're past halfway
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append(chunk.strip())
            start = end - overlap  # Move with overlap
            
        return chunks

    async def create_embeddings(self, chunks: List[str], document_id: str):
        """Create embeddings and store in Pinecone"""
        try:
            if not self.cohere.client or not self.pinecone.index:
                logger.warning("Embedding services not available")
                return
            
            # Generate embeddings using Cohere
            embeddings_response = self.cohere.client.embed(
                texts=chunks,
                model='embed-english-v3.0',
                input_type='search_document'
            )
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings_response.embeddings)):
                vectors.append({
                    'id': f"{document_id}_{i}",
                    'values': embedding,
                    'metadata': {
                        'document_id': document_id,
                        'chunk_index': i,
                        'text': chunk[:1000]  # Store first 1000 chars as metadata
                    }
                })
            
            # Upsert to Pinecone
            self.pinecone.index.upsert(vectors=vectors)
            logger.info(f"Created {len(vectors)} embeddings for document {document_id}")
            
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")

    async def query_rag(self, question: str, doc_id: str) -> Dict[str, Any]:
        """Query using RAG (Retrieval Augmented Generation)"""
        try:
            # If vector search is available, use it
            if self.cohere.client and self.pinecone.index:
                # Generate query embedding
                query_embedding = self.cohere.client.embed(
                    texts=[question],
                    model='embed-english-v3.0',
                    input_type='search_query'
                ).embeddings[0]
                
                # Search in Pinecone
                search_results = self.pinecone.index.query(
                    vector=query_embedding,
                    filter={'document_id': doc_id},
                    top_k=3,
                    include_metadata=True
                )
                
                # Extract relevant chunks
                context = "\n".join([
                    match['metadata']['text'] 
                    for match in search_results['matches']
                    if match['score'] > 0.7  # Relevance threshold
                ])
                
                if context and self.gemini.model:
                    # Generate answer using Gemini with context
                    prompt = f"""Based on the following context from the document, answer the question.
                    
                    Context:
                    {context}
                    
                    Question: {question}
                    
                    Provide a clear, concise answer based only on the provided context. If the answer cannot be found in the context, say so.
                    """
                    
                    response = self.gemini.model.generate_content(prompt)
                    
                    return {
                        "answer": response.text if response.text else "Could not generate answer",
                        "sources": [match['metadata']['chunk_index'] for match in search_results['matches'][:3]],
                        "confidence": search_results['matches'][0]['score'] if search_results['matches'] else 0.0
                    }
            
            # Fallback if RAG not available
            return {
                "answer": f"I'll help you with: {question}. However, advanced document analysis is currently unavailable.",
                "sources": [],
                "confidence": 0.5
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "answer": "Sorry, I couldn't process your question at this time.",
                "sources": [],
                "confidence": 0.0
            }

ai_services = AIServices()

def init_ai_services():
    ai_services.initialize()
    logger.info("✅ AI Services initialized")