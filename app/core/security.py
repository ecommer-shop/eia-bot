"""Verificación opcional de las peticiones entrantes al bot."""
import hashlib
import hmac
import logging
import time

from fastapi import Header, HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Chatwoot firma "<timestamp>.<cuerpo>"; se rechaza lo que se desvíe más de esto (anti-repetición).
TOLERANCIA_SEGUNDOS = 300


def _no_autorizado(motivo: str) -> HTTPException:
    logger.warning("Petición rechazada: %s", motivo)
    return HTTPException(status_code=401, detail="No autorizado")


async def verify_chatwoot_signature(
    request: Request,
    x_chatwoot_signature: str | None = Header(default=None),
    x_chatwoot_timestamp: str | None = Header(default=None),
) -> None:
    """Valida `X-Chatwoot-Signature: sha256=<hmac>` solo si CHATWOOT_WEBHOOK_SECRET está definido."""
    secret = settings.chatwoot_webhook_secret
    if not secret:
        return
    if not x_chatwoot_signature or not x_chatwoot_timestamp:
        raise _no_autorizado("faltan cabeceras de firma")
    try:
        ts = int(x_chatwoot_timestamp)
    except ValueError:
        raise _no_autorizado("timestamp inválido")
    if abs(time.time() - ts) > TOLERANCIA_SEGUNDOS:
        raise _no_autorizado("timestamp fuera de tolerancia")

    body = await request.body()
    esperado = "sha256=" + hmac.new(
        secret.encode(), x_chatwoot_timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(esperado, x_chatwoot_signature):
        raise _no_autorizado("firma inválida")


async def require_bot_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Exige `X-API-Key` en los endpoints de prueba solo si BOT_API_KEY está definida."""
    expected = settings.bot_api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise _no_autorizado("clave de API ausente o inválida")
