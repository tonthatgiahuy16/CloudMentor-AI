from fastapi import FastAPI

from app.api.chat import router


app = FastAPI(
    title="CloudMentor AI"
)


app.include_router(
    router
)


@app.get("/")
def root():

    return {
        "message":
        "CloudMentor AI API running"
    }