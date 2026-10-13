from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

# 503 de eia-chat = tienda sin clave Bifrost (error de creación/renovación de
# claves). El cliente ve un mensaje amigable en vez de silencio.
SIN_CLAVE_BIFROST_MESSAGE = (
    "¡Gracias por escribir! Estamos presentando un inconveniente técnico "
    "momentáneamente. Un asistente humano te atenderá muy pronto."
)

# Timeout o 5xx de eia-chat (Bifrost lento o caído): mismo mensaje amigable.
TECHNICAL_ISSUE_MESSAGE = SIN_CLAVE_BIFROST_MESSAGE

# Timeout total eia-bot → eia-chat. El pipeline hace 2 llamadas al LLM
# (clasificar + responder); 90s cubre el caso lento sin dejar al usuario
# sin respuesta (el fallback amigable cubre el resto).
EIA_CHAT_TIMEOUT = httpx.Timeout(90.0, connect=5.0)


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

    try:
        async with httpx.AsyncClient(timeout=EIA_CHAT_TIMEOUT) as client:
            response = await client.post(
                settings.simetria_api_url,
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException as error:
        print("=== EIA RAG TIMEOUT ===", flush=True)
        print(str(error), flush=True)
        return EiaRagResponse(
            answer=TECHNICAL_ISSUE_MESSAGE,
            raw={"error": "timeout", "detail": str(error)},
        )

    if response.status_code == 503:
        detail = ""
        try:
            detail = str(response.json().get("detail") or "")
        except Exception:
            detail = response.text[:300]

        print("=== EIA RAG 503 (tienda sin clave Bifrost) ===", flush=True)
        print(detail, flush=True)

        return EiaRagResponse(
            answer=SIN_CLAVE_BIFROST_MESSAGE,
            raw={"error": "sin_clave_bifrost", "detail": detail},
        )

    if response.status_code >= 500:
        detail = response.text[:300]
        print("=== EIA RAG 5xx ===", flush=True)
        print(f"status={response.status_code} {detail}", flush=True)
        return EiaRagResponse(
            answer=TECHNICAL_ISSUE_MESSAGE,
            raw={"error": "eia_chat_5xx", "status": response.status_code},
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
