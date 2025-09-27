import cohere
import os
import logging

logger = logging.getLogger(__name__)

class CohereService:
    def __init__(self):
        self.client = None

    def initialize(self):
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            logger.warning("COHERE_API_KEY not set - embeddings disabled")
            return
        try:
            self.client = cohere.Client(api_key)
            logger.info("✅ Cohere initialized")
        except Exception as e:
            logger.warning(f"Cohere initialization failed: {e}")