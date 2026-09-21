import httpx

from app.core.config import settings


def send_message_to_chatwoot(
    conversation_id: int,
    content: str,
    account_id: int | str | None = None,
) -> dict:
    account_id = account_id or settings.chatwoot_account_id

    if not account_id:
        raise ValueError("No se encontró account_id de Chatwoot")

    url = (
        f"{settings.chatwoot_base_url}/api/v1/accounts/"
        f"{account_id}/conversations/"
        f"{conversation_id}/messages"
    )

    headers = {
        "Content-Type": "application/json",
        "api_access_token": settings.chatwoot_api_access_token,
    }

    payload = {
        "content": content,
        "message_type": "outgoing",
        "private": False,
        "content_type": "text",
    }

    print("=== CHATWOOT SEND URL ===", flush=True)
    print(url, flush=True)

    response = httpx.post(
        url,
        json=payload,
        headers=headers,
        timeout=60.0,
    )

    response.raise_for_status()

    return response.json()