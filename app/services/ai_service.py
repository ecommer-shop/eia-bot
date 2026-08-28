import logging

from app.core.config import settings
from app.core.http import get_client

logger = logging.getLogger(__name__)


async def get_ai_response(prompt: str) -> str:
    if not settings.simetria_api_url:
        raise ValueError("No se encontró SIMETRIA_API_URL en el archivo .env")

    headers = {
        "Content-Type": "application/json"
    }

    if settings.simetria_api_key:
        headers["Authorization"] = f"Bearer {settings.simetria_api_key}"

    payload = {
        "query": prompt
    }

    response = await get_client().post(
        settings.simetria_api_url,
        json=payload,
        headers=headers,
        timeout=settings.ai_timeout_seconds,
    )

    response.raise_for_status()

    data = response.json()

    for field in ("response", "answer", "message", "text"):
        if field in data:
            return data[field]

    logger.warning("respuesta del RAG sin campo conocido: %s", sorted(data))

    return str(data)
