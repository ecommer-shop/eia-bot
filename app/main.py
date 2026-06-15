"""
Aplicación FastAPI — punto de entrada.

Endpoints:
- GET  /                     → health check
- POST /webhook/chatwoot     → recibe el Agent Bot de Chatwoot (mensajes entrantes)
- POST /webhook/chatwoot/status → (opcional) recibe cambios de estado de Chatwoot
                                  para reactivar el bot cuando el agente resuelve

Arquitectura: Chatwoot recibe WhatsApp → Agent Bot llama aquí → Phi-4 responde
→ Chatwoot entrega al cliente. Una sola fuente de verdad, sin bucles.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.webhook import ChatwootWebhook
from app.services import conversation
from app.models import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await db.init_db()
    yield
    # shutdown
    await db.close_db()


app = FastAPI(title="ecommer WhatsApp Bot", lifespan=lifespan)


@app.get("/")
async def health():
    return {"status": "ok", "service": "ecommer-bot"}


@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    """
    Recibe el payload del Agent Bot de Chatwoot.

    Validamos con Pydantic y delegamos la decisión al orquestador.
    Respondemos 200 SIEMPRE (aunque ignoremos el mensaje) para que
    Chatwoot no reintente y no se generen duplicados.
    """
    raw = await request.json()

    # Chatwoot a veces envuelve los datos; aceptamos ambas formas
    data = raw.get("body", raw) if isinstance(raw, dict) else raw

    try:
        payload = ChatwootWebhook(**data)
    except Exception as e:
        print(f"[webhook] Payload no válido: {e}")
        return JSONResponse({"status": "ignored", "reason": "payload inválido"}, 200)

    # El filtro clave: solo procesamos mensajes reales de clientes
    if not payload.is_from_customer():
        return JSONResponse({"status": "ignored", "reason": "no es de cliente"}, 200)

    result = await conversation.handle_message(payload)
    return JSONResponse(result, 200)


@app.post("/webhook/chatwoot/status")
async def chatwoot_status_webhook(request: Request):
    """
    Opcional: si configuras un webhook de 'conversation_resolved' en Chatwoot,
    aquí reactivamos el bot cuando el agente cierra la conversación.
    """
    raw = await request.json()
    data = raw.get("body", raw) if isinstance(raw, dict) else raw

    event = data.get("event")
    status = (data.get("status") or
              (data.get("conversation", {}) or {}).get("status"))
    conv = data.get("conversation", {}) or {}
    conv_id = conv.get("id") or data.get("id")

    # Cuando el agente marca 'resolved', devolvemos el control al bot
    if conv_id and (event == "conversation_resolved" or status == "resolved"):
        await db.set_handoff(int(conv_id), False)
        return JSONResponse({"status": "bot_reactivado", "conversation_id": conv_id}, 200)

    return JSONResponse({"status": "ok"}, 200)
