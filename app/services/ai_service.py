import httpx

from app.core.config import settings


def get_ai_response(
    prompt: str,
    conversation_id: str | None = None,
    inbox_id: int | str | None = None,
    user_id: int | str | None = None,
    channel: str | None = None,
    account_id: int | str | None = None,
) -> str:
    if not settings.simetria_api_url:
        raise ValueError("No se encontró SIMETRIA_API_URL en el archivo .env")

    headers = {
        "Content-Type": "application/json"
    }

    if settings.simetria_api_key:
        headers["Authorization"] = f"Bearer {settings.simetria_api_key}"

    payload = {
        "query": prompt,
    }

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    if inbox_id is not None:
        payload["inbox_id"] = int(inbox_id)

    if user_id is not None:
        payload["user_id"] = str(user_id)

    if channel is not None:
        payload["channel"] = channel

    if account_id is not None:
        payload["account_id"] = int(account_id)

    print("=== SIMETRIA PAYLOAD ===", flush=True)
    print(payload, flush=True)

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