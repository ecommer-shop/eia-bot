from app.core.config import settings
from app.core.http import get_client


async def send_message_to_chatwoot(conversation_id: int, content: str) -> dict:
    url = (
        f"{settings.chatwoot_base_url}/api/v1/accounts/"
        f"{settings.chatwoot_account_id}/conversations/"
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

    response = await get_client().post(
        url,
        json=payload,
        headers=headers,
        timeout=settings.chatwoot_timeout_seconds,
    )

    response.raise_for_status()

    return response.json()
