from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.upload import router as upload_router
from app.api.subjects import router as subjects_router

app = FastAPI(
    title="CloudMentor AI",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
def root():
    return {
        "message": "CloudMentor AI API running",
    }
