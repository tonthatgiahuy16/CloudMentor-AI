from fastapi import FastAPI

app = FastAPI(
    title="CloudMentor AI",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "CloudMentor AI is running!"
    }