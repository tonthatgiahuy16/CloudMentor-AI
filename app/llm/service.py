from google import genai

from app.llm.config import (
    GEMINI_API_KEY,
    MODEL_NAME
)


class GeminiService:

    def __init__(self):

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )


    def generate(
        self,
        prompt: str
    ) -> str:
        print("Using model:", MODEL_NAME)

        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text