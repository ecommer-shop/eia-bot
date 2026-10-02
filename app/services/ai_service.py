"""Generacion de respuestas: RAG primero, Phi-4 como red de seguridad.

El RAG de ecommer devuelve HTTP 200 incluso cuando su LLM falla: el error
queda dentro del campo `answer` como un texto de disculpa. Por eso no basta
con capturar errores de red; hay que reconocer tambien esa respuesta
degradada y recurrir al modelo de respaldo.
"""

import logging
import unicodedata

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.http import get_client

logger = logging.getLogger(__name__)

_phi4: AsyncOpenAI | None = None


def _get_phi4() -> AsyncOpenAI | None:
    """Cliente de Azure, creado solo si hay credenciales configuradas."""
    global _phi4

    if not settings.azure_ai_endpoint or not settings.azure_ai_key:
        return None

    if _phi4 is None:
        _phi4 = AsyncOpenAI(
            base_url=settings.azure_ai_endpoint,
            api_key=settings.azure_ai_key,
        )

    return _phi4


async def close_phi4() -> None:
    global _phi4

    if _phi4 is not None:
        await _phi4.close()
        _phi4 = None


def _normalize(text: str) -> str:
    """Minusculas y sin tildes, para que la deteccion no dependa del acento."""
    sin_tildes = unicodedata.normalize("NFD", text)
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.casefold()


def is_degraded_answer(answer: str) -> bool:
    """True si el RAG respondio con su mensaje de fallo en vez de contenido."""
    if not answer or not answer.strip():
        return True

    normalizada = _normalize(answer)

    return any(_normalize(m) in normalizada for m in settings.rag_fallback_markers)


_CHANNEL_NAMES = {
    "whatsapp": "whatsapp",
    "instagram": "instagram",
    "facebookpage": "messenger",
    "webwidget": "shop",
}


def normalize_channel(channel: str | None) -> str | None:
    """'Channel::FacebookPage' -> 'messenger', 'Channel::Whatsapp' -> 'whatsapp'."""
    if not channel:
        return None
    key = str(channel).split("::")[-1].lower()
    return _CHANNEL_NAMES.get(key, key)


def build_rag_payload(message: str, context: dict | None) -> dict:
    """Mensaje limpio + identidad del comercio.

    El gateway elige la tienda por inbox/cuenta y guarda su propia memoria por
    conversation_id, asi que no se pega el historial dentro de la consulta (eso
    ensuciaba la clasificacion y la busqueda). El conversation_id va con la
    cuenta porque los IDs de Chatwoot se repiten entre cuentas.
    """
    payload: dict = {"query": message}
    context = context or {}

    account_id = context.get("account_id")
    conversation_id = context.get("conversation_id")

    if account_id is not None:
        payload["account_id"] = account_id
    if context.get("inbox_id") is not None:
        payload["inbox_id"] = context["inbox_id"]
    if conversation_id is not None:
        payload["conversation_id"] = (
            f"{account_id}-{conversation_id}" if account_id is not None else str(conversation_id)
        )
    channel = normalize_channel(context.get("channel"))
    if channel:
        payload["channel"] = channel

    return payload


async def ask_rag(message: str, context: dict | None = None) -> str:
    if not settings.simetria_api_url:
        raise ValueError("No se encontró SIMETRIA_API_URL en el archivo .env")

    headers = {
        "Content-Type": "application/json"
    }

    if settings.simetria_api_key:
        headers["Authorization"] = f"Bearer {settings.simetria_api_key}"

    response = await get_client().post(
        settings.simetria_api_url,
        json=build_rag_payload(message, context),
        headers=headers,
        timeout=settings.ai_timeout_seconds,
    )

    response.raise_for_status()

    data = response.json()

    for field in ("response", "answer", "message", "text"):
        if field in data:
            return data[field]

    logger.warning("respuesta del RAG sin campo conocido: %s", sorted(data))

    return str(data)


async def ask_phi4(user_message: str, history: list[dict] | None = None) -> str:
    client = _get_phi4()

    if client is None:
        raise RuntimeError("Azure Phi-4 no está configurado")

    messages: list[dict] = [
        {"role": "system", "content": settings.default_system_prompt}
    ]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})

    respuesta = await client.chat.completions.create(
        model=settings.azure_ai_deployment,
        messages=messages,
        temperature=0.4,
        max_tokens=400,
    )

    return respuesta.choices[0].message.content.strip()


async def generate_reply(
    user_message: str,
    history: list[dict] | None = None,
    context: dict | None = None,
) -> str:
    """Devuelve la respuesta para el cliente, con respaldo si el RAG falla."""
    motivo = None

    try:
        answer = await ask_rag(user_message, context)

        if not is_degraded_answer(answer):
            return answer

        motivo = "el RAG respondió con su mensaje de fallo"

    except Exception as error:
        motivo = f"{type(error).__name__}: {error}"

    logger.warning("recurriendo a Phi-4 porque %s", motivo)

    try:
        return await ask_phi4(user_message, history)
    except Exception:
        logger.exception("Phi-4 tampoco pudo responder")

    return settings.fallback_message
