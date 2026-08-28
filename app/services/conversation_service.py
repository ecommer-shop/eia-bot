"""Procesamiento de un mensaje entrante, fuera del request del webhook.

Chatwoot corta la peticion a los 5 segundos y, si falla, abre la conversacion
a un agente humano y deja un mensaje de actividad visible. Consultar al RAG
tarda mas que eso, asi que el webhook responde de inmediato y todo el trabajo
ocurre aqui, en segundo plano.
"""

import logging

from app.services.ai_service import generate_reply
from app.services.chatwoot_service import send_message_to_chatwoot
from app.services.memory_service import add_message_to_memory, get_conversation_memory

logger = logging.getLogger(__name__)


async def process_message(parsed: dict) -> None:
    conversation_id = parsed["conversation_id"]
    user_message = parsed["query"]

    try:
        history = await get_conversation_memory(conversation_id)
        ai_response = await generate_reply(user_message, history)
    except Exception:
        logger.exception(
            "fallo generando la respuesta conversation_id=%s inbox_id=%s",
            conversation_id,
            parsed.get("inbox_id"),
        )
        return

    try:
        await send_message_to_chatwoot(
            conversation_id=conversation_id,
            content=ai_response,
        )
    except Exception:
        logger.exception(
            "fallo enviando la respuesta a Chatwoot conversation_id=%s",
            conversation_id,
        )
        return

    await add_message_to_memory(conversation_id, "user", user_message)
    await add_message_to_memory(conversation_id, "assistant", ai_response)

    logger.info(
        "respuesta entregada conversation_id=%s inbox_id=%s channel=%s",
        conversation_id,
        parsed.get("inbox_id"),
        parsed.get("channel"),
    )
