from pinecone import Pinecone, ServerlessSpec
import os
import logging

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.client = None
        self.index = None

    def initialize(self):
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.warning("PINECONE_API_KEY not set - vector store disabled")
            return
        try:
            self.client = Pinecone(api_key=api_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "document-analyzer")
            try:
                self.client.describe_index(index_name)
                logger.info(f"✅ Connected to Pinecone index: {index_name}")
            except Exception:
                self.client.create_index(
                    name=index_name,
                    dimension=1024,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
                logger.info(f"✅ Created Pinecone index: {index_name}")
            self.index = self.client.Index(index_name)
        except Exception as e:
            logger.warning(f"Pinecone initialization failed: {e}")