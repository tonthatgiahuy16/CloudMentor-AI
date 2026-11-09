from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.demo_seed import router as demo_seed_router
from app.api.health import router as health_router
from app.api.quizzes import router as quizzes_router
from app.api.upload import router as upload_router
from app.api.subjects import router as subjects_router
from app.core.config import CORS_ALLOWED_ORIGINS

app = FastAPI(
    title="CloudMentor AI",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(demo_seed_router)

app.include_router(
    subjects_router
)

app.include_router(
    chat_router
)

app.include_router(
    upload_router
)

app.include_router(
    documents_router
)

app.include_router(
    quizzes_router
)


@app.get("/")
def root():
    return {
        "message": "CloudMentor AI API running",
    }
