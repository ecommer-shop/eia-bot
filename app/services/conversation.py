"""
Orquestador de conversación — el cerebro que une todo.

Decide, para cada mensaje entrante del cliente:
1. ¿La conversación ya está en manos de un humano? → no responder
2. ¿El cliente pide un humano? → activar handoff, avisar al agente, callar al bot
3. Si no → generar respuesta con Phi-4 y enviarla por Chatwoot

Aquí vive la lógica que en N8N estaba dispersa entre IF, Switch y nodos HTTP.
"""
from app.config import get_settings
from app.schemas.webhook import ChatwootWebhook
from app.services import chatwoot, ai_agent
from app.models import database as db

settings = get_settings()


def _wants_human(text: str) -> bool:
    """Detecta si el cliente pide explícitamente un agente humano."""
    low = text.lower()
    return any(kw in low for kw in settings.HANDOFF_KEYWORDS)


async def handle_message(payload: ChatwootWebhook) -> dict:
    """
    Punto de entrada para cada webhook entrante.
    Devuelve un dict con el resultado (útil para logs y para la respuesta HTTP).
    """
    conv_id = payload.conversation_id()
    account_id = payload.account_id()
    text = payload.content or ""

    if conv_id is None:
        return {"status": "ignored", "reason": "sin conversation_id"}

    # 1) Si un humano ya tomó la conversación, el bot se calla
    if await db.get_handoff(conv_id):
        return {"status": "skipped", "reason": "handoff activo"}

    # 2) ¿El cliente pide un humano?
    if _wants_human(text):
        await db.set_handoff(conv_id, True)
        await chatwoot.toggle_status(account_id, conv_id, "open")
        await chatwoot.send_private_note(
            account_id, conv_id,
            "🔔 El cliente solicitó atención humana. El bot quedó en pausa "
            "para esta conversación.",
        )
        await chatwoot.send_message(
            account_id, conv_id,
            "Con gusto. Te estoy conectando con una persona del equipo, "
            "en un momento te atienden. 🙌",
        )
        return {"status": "handoff", "conversation_id": conv_id}

    # 3) Flujo normal: responder con Phi-4
    history = await db.get_history(conv_id)
    system_prompt = await db.get_system_prompt(None)  # multi-tenant: luego por inbox

    reply = await ai_agent.generate_reply(system_prompt, history, text)

    # Guardar ambos turnos en memoria persistente
    await db.append_history(conv_id, account_id, "user", text)
    await db.append_history(conv_id, account_id, "assistant", reply)

    # Enviar la respuesta al cliente vía Chatwoot
    await chatwoot.send_message(account_id, conv_id, reply)

    return {"status": "replied", "conversation_id": conv_id}
