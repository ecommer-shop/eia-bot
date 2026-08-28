import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.http import close_client
from app.core.redis import close_redis

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_client()
    await close_redis()


app = FastAPI(
    title="Chatbot API",
    description="API base para proyecto de chatbot",
    version="0.1.0",
    lifespan=lifespan,
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
