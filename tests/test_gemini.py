from app.llm.service import GeminiService

llm = GeminiService()

answer = llm.generate(
    "Giải thích điện toán đám mây trong khoảng 3 câu."
)

print(answer)