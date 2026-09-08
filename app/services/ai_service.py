import logging

import httpx

from app.core.config import settings
from app.schemas.chat import RagRequest, RagResponse

logger = logging.getLogger(__name__)


async def call_eia_rag(
    query: str,
    conversation_id: str,
    inbox_id: int,
    user_id: int | None = None,
    channel: str | None = None,
) -> RagResponse:
    payload = RagRequest(
        query=query,
        conversation_id=conversation_id,
        inbox_id=inbox_id,
        user_id=user_id,
        channel=channel,
    )

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"{settings.eia_rag_url}/agent/chat",
                json=payload.model_dump(),
            )
            resp.raise_for_status()
            return RagResponse(**resp.json())
        except httpx.TimeoutException:
            logger.error(
                "Timeout llamando a eia-rag, conversation_id=%s",
                conversation_id,
            )
            return RagResponse(
                answer="Dame un momento, estoy teniendo problemas para responder. Un agente te va a contactar pronto.",
                intent_detected="ERROR",
                sources_used=0,
                conversation_id=conversation_id,
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "eia-rag devolvió %d: %s",
                e.response.status_code,
                e.response.text,
            )
            return RagResponse(
                answer="Dame un momento, estoy teniendo problemas para responder.",
                intent_detected="ERROR",
                sources_used=0,
                conversation_id=conversation_id,
            )