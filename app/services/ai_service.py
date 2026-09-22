from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class EiaRagResponse:
    answer: str
    raw: dict[str, Any] | None = None


async def call_eia_rag(
    query: str,
    conversation_id: str = "test",
    inbox_id: int | str = 0,
    user_id: int | str | None = None,
    channel: str | None = None,
    account_id: int | str | None = None,
) -> EiaRagResponse:
    if not settings.simetria_api_url:
        raise ValueError("No se encontró SIMETRIA_API_URL, EIA_RAG_URL o RAG_BASE_URL")

    headers = {
        "Content-Type": "application/json"
    }

    if settings.simetria_api_key:
        headers["Authorization"] = f"Bearer {settings.simetria_api_key}"

    payload: dict[str, Any] = {
        "query": query,
        "conversation_id": conversation_id,
        "inbox_id": int(inbox_id or 0),
    }

    if user_id is not None:
        payload["user_id"] = str(user_id)

    if channel is not None:
        payload["channel"] = channel

    if account_id is not None:
        payload["account_id"] = int(account_id)

    print("=== EIA RAG PAYLOAD ===", flush=True)
    print(payload, flush=True)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.simetria_api_url,
            json=payload,
            headers=headers,
        )

    response.raise_for_status()

    data = response.json()

    answer = (
        data.get("answer")
        or data.get("response")
        or data.get("message")
        or data.get("text")
        or str(data)
    )

    return EiaRagResponse(
        answer=answer,
        raw=data
    )


async def get_ai_response(
    prompt: str,
    conversation_id: str | None = None,
    inbox_id: int | str | None = None,
    user_id: int | str | None = None,
    channel: str | None = None,
    account_id: int | str | None = None,
) -> str:
    result = await call_eia_rag(
        query=prompt,
        conversation_id=conversation_id or "test",
        inbox_id=inbox_id or 0,
        user_id=user_id,
        channel=channel,
        account_id=account_id,
    )

    return result.answer
