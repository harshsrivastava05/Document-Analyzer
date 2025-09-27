import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None

    def initialize(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=api_key)

        model_names = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro'
        ]

        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                test_response = model.generate_content(
                    "Hello",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=50
                    )
                )
                if test_response and test_response.text:
                    self.model = model
                    logger.info(f"✅ Gemini initialized with model: {name}")
                    break
            except Exception as e:
                logger.warning(f"Failed to init Gemini model {name}: {e}")
                continue
        if not self.model:
            raise ValueError("Failed to initialize any Gemini model.")
