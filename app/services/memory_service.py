import json
from redis import Redis

from app.core.config import settings


redis_client = None

if settings.valkey_url:
    redis_client = Redis.from_url(
        settings.valkey_url,
        decode_responses=True
    )


def get_memory_key(conversation_id) -> str:
    return f"eia-bot:chatwoot:conversation:{conversation_id}:messages"


def get_conversation_memory(conversation_id) -> list[dict]:
    if redis_client is None:
        return []

    key = get_memory_key(conversation_id)
    raw_items = redis_client.lrange(key, 0, -1)

    messages = []

    for item in raw_items:
        try:
            messages.append(json.loads(item))
        except json.JSONDecodeError:
            continue

    return messages


def add_message_to_memory(
    conversation_id,
    role: str,
    content: str,
    max_messages: int = 12,
    ttl_seconds: int = 86400
) -> None:
    if redis_client is None:
        return

    key = get_memory_key(conversation_id)

    item = {
        "role": role,
        "content": content
    }

    redis_client.rpush(key, json.dumps(item, ensure_ascii=False))
    redis_client.ltrim(key, -max_messages, -1)
    redis_client.expire(key, ttl_seconds)


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