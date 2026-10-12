"""Cliente HTTP asincrono compartido.

Antes se creaba un cliente nuevo en cada llamada, lo que impedia reutilizar
conexiones. Aqui se mantiene uno por proceso y se cierra en el shutdown de
la aplicacion.
"""

import httpx

from app.core.config import settings

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ai_timeout_seconds, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    return _client


async def close_client() -> None:
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
