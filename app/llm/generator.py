from app.llm.service import GeminiService
from app.llm.prompt import SYSTEM_PROMPT


class AnswerGenerator:

    def __init__(self):

        self.llm = GeminiService()


    def build_prompt(
        self,
        question,
        contexts
    ):

        context_text = "\n\n".join(
            contexts
        )

        prompt = f"""
{SYSTEM_PROMPT}


Context:

{context_text}


Question:

{question}
"""

        return prompt


    def generate(
        self,
        question,
        contexts
    ):

        prompt = self.build_prompt(
            question,
            contexts
        )

        answer = self.llm.generate(
            prompt
        )

        return answer