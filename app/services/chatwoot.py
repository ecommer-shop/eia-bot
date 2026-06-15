"""
Cliente de la API de Chatwoot.

Responsabilidades:
- Enviar la respuesta del bot a la conversación (POST /messages)
- Cambiar el estado de la conversación (open/resolved) para el handoff

Toda la comunicación de salida hacia el cliente de WhatsApp pasa por aquí:
nosotros respondemos a Chatwoot, y Chatwoot reenvía a WhatsApp por su canal
nativo Cloud API. Así no tocamos directamente la API de Meta.
"""
import httpx
from app.config import get_settings

settings = get_settings()


def _headers() -> dict:
    return {
        "api_access_token": settings.CHATWOOT_API_TOKEN,
        "Content-Type": "application/json",
    }


def _base(account_id: int) -> str:
    return f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"


async def send_message(account_id: int, conversation_id: int, content: str) -> bool:
    """
    Envía un mensaje saliente del bot a la conversación.
    message_type=outgoing hace que Chatwoot lo entregue al cliente por WhatsApp.
    """
    url = f"{_base(account_id)}/conversations/{conversation_id}/messages"
    payload = {
        "content": content,
        "message_type": "outgoing",
        "private": False,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(url, json=payload, headers=_headers())
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"[chatwoot] Error enviando mensaje: {e}")
            return False


async def send_private_note(account_id: int, conversation_id: int, content: str) -> bool:
    """
    Envía una nota privada (solo la ve el agente, no el cliente).
    Útil para avisar 'Cliente solicitó atención humana'.
    """
    url = f"{_base(account_id)}/conversations/{conversation_id}/messages"
    payload = {"content": content, "message_type": "outgoing", "private": True}
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(url, json=payload, headers=_headers())
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"[chatwoot] Error enviando nota privada: {e}")
            return False


async def toggle_status(account_id: int, conversation_id: int, status: str) -> bool:
    """
    Cambia el estado de la conversación.
    status: 'open' (visible para agentes) | 'resolved' | 'pending'
    Llamamos 'open' al activar handoff para que aparezca en la bandeja.
    """
    url = f"{_base(account_id)}/conversations/{conversation_id}/toggle_status"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(url, json={"status": status}, headers=_headers())
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"[chatwoot] Error cambiando estado: {e}")
            return False
