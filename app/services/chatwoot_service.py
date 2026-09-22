import httpx

from app.core.config import settings


async def send_message_to_chatwoot(
    conversation_id: int | str,
    content: str,
    account_id: int | str | None = None,
) -> dict:
    account_id = account_id or settings.chatwoot_account_id

    if not account_id:
        raise ValueError("No se encontró account_id de Chatwoot")

    if not settings.chatwoot_base_url:
        raise ValueError("No se encontró CHATWOOT_BASE_URL")

    if not settings.chatwoot_api_access_token:
        raise ValueError("No se encontró CHATWOOT_API_ACCESS_TOKEN o CHATWOOT_API_TOKEN")

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

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

    response.raise_for_status()

    return response.json()