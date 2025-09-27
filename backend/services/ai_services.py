# services/ai_services.py
from services.ai.gemini_service import GeminiService
from services.embeddings.cohere_service import CohereService
from services.vectorstore.pinecone_service import PineconeService
import logging

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

    # expose helpers for your routers
    async def analyze_document(self, *args, **kwargs):
        return await self.gemini.model.generate_content(*args, **kwargs)

    async def query_rag(self, question: str, doc_id: str):
        # combine Gemini + Pinecone + Cohere if available
        return {
            "answer": f"Simulated RAG answer for: {question}",
            "sources": [doc_id],
            "confidence": 0.9,
        }

ai_services = AIServices()

def init_ai_services():
    ai_services.initialize()
    logger.info("✅ AI Services initialized")
