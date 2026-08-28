"""Deduplicacion de entregas de webhook.

Chatwoot reintenta la entrega hasta 3 veces cuando el bot responde 429 o 500
(RETRYABLE_AGENT_BOT_STATUSES en lib/webhooks/trigger.rb). Sin esta guarda, un
reintento genera una segunda respuesta al cliente por el mismo mensaje.
"""

import logging

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


def _key(delivery_key: str) -> str:
    return f"eia-bot:chatwoot:delivery:{delivery_key}"


async def is_first_delivery(delivery_key: str) -> bool:
    """True si es la primera vez que se ve esta entrega.

    Ante un fallo de Valkey se responde True: es preferible arriesgar un
    mensaje duplicado a dejar de atender al cliente.
    """
    client = get_redis()

    if client is None:
        return True

    try:
        created = await client.set(
            _key(delivery_key),
            "1",
            nx=True,
            ex=settings.dedup_ttl_seconds,
        )
    except Exception:
        logger.exception("no se pudo deduplicar delivery_key=%s", delivery_key)
        return True

    return bool(created)
