"""Cliente Valkey/Redis asincrono compartido.

Se usa la variante asincrona de redis-py: las llamadas ocurren dentro del
event loop, y un cliente sincrono lo bloquearia para todas las conversaciones
a la vez.
"""

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis | None:
    """Devuelve el cliente, o None si no hay Valkey configurado."""
    global _client

    if _client is None and settings.valkey_url:
        _client = Redis.from_url(settings.valkey_url, decode_responses=True)

    return _client


async def close_redis() -> None:
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
