from google import genai
from app.llm.config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

models = [
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
    "models/gemini-3.5-flash-lite",
    "models/gemini-3.1-flash-lite",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash",
]

for model in models:
    try:
        response = client.models.generate_content(
            model=model,
            contents="Xin chào"
        )
        print(f"✅ {model}: OK")
    except Exception as e:
        print(f"❌ {model}: {e}")