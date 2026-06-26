import httpx

from app.core.config import settings


def get_ai_response(prompt: str) -> str:
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

    response = httpx.post(
        settings.simetria_api_url,
        json=payload,
        headers=headers,
        timeout=60.0,
    )

    response.raise_for_status()

    data = response.json()

    if "response" in data:
        return data["response"]

    if "answer" in data:
        return data["answer"]

    if "message" in data:
        return data["message"]

    if "text" in data:
        return data["text"]

    return str(data)