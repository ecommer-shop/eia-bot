from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Chatbot API",
    description="API base para proyecto de chatbot",
    version="0.1.0",
)

app.include_router(router)


@app.get("/")
def home():
    return {
        "message": "API funcionando correctamente"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }