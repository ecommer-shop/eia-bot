import json
import logging

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


def get_memory_key(conversation_id, account_id=None) -> str:
    scope = f"{account_id}:" if account_id else ""
    return f"eia-bot:chatwoot:conversation:{scope}{conversation_id}:messages"


async def get_conversation_memory(conversation_id, account_id=None) -> list[dict]:
    client = get_redis()

    if client is None:
        return []

    key = get_memory_key(conversation_id, account_id)

    try:
        raw_items = await client.lrange(key, 0, -1)
    except Exception:
        logger.exception("no se pudo leer la memoria conversation_id=%s", conversation_id)
        return []

    messages = []

    for item in raw_items:
        try:
            messages.append(json.loads(item))
        except json.JSONDecodeError:
            continue

    return messages


async def add_message_to_memory(
    conversation_id,
    role: str,
    content: str,
    max_messages: int = 12,
    ttl_seconds: int = 86400,
    account_id=None,
) -> None:
    client = get_redis()

    if client is None:
        return

    key = get_memory_key(conversation_id, account_id)

    item = {
        "role": role,
        "content": content
    }

    try:
        async with client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, json.dumps(item, ensure_ascii=False))
            pipe.ltrim(key, -max_messages, -1)
            pipe.expire(key, ttl_seconds)
            await pipe.execute()
    except Exception:
        logger.exception("no se pudo guardar en memoria conversation_id=%s", conversation_id)


def build_context_prompt(history: list[dict], current_message: str) -> str:
    if not history:
        return current_message

    history_text = ""

    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "assistant":
            history_text += f"Asistente: {content}\n"
        else:
            history_text += f"Cliente: {content}\n"

    return (
        "Ten en cuenta el siguiente historial reciente de la conversación:\n\n"
        f"{history_text}\n"
        "Mensaje actual del cliente:\n"
        f"{current_message}"
    )
