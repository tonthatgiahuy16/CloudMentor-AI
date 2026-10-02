from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.chat import router
from app.api.documents import router as documents_router


app = FastAPI(
    title="CloudMentor AI"
)


app.include_router(
    router
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
        "message":
        "CloudMentor AI API running"
    }