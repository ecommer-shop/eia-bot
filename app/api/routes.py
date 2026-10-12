import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import ask_rag as get_ai_response
from app.services.chatwoot_parser import parse_chatwoot_webhook
from app.services.conversation_service import process_message
from app.services.dedup_service import is_first_delivery

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["API"]
)


@router.get("/hello")
def hello():
    return {
        "message": "Hola desde la API"
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await get_ai_response(request.prompt)

        return ChatResponse(
            response=response
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        logger.exception("fallo atendiendo /chat")

        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la API de Simetria: {str(error)}"
        )


@router.post("/chatwoot-webhook", summary="Chatwoot Webhook")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """Recibe el evento del Agent Bot y responde de inmediato.

    Chatwoot corta la peticion a los 5 segundos (WEBHOOK_TIMEOUT) y reintenta
    hasta 3 veces si el bot responde 429 o 500. Por eso este endpoint nunca
    hace trabajo lento ni devuelve error: valida, encola y responde 200. La
    consulta al RAG y el envio de la respuesta ocurren en segundo plano.
    """
    try:
        payload = await request.json()
    except Exception:
        logger.warning("el cuerpo del webhook no es JSON válido")

        return {
            "ignored": True,
            "reason": "Payload no es JSON válido"
        }

    parsed = parse_chatwoot_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Evento no válido, mensaje vacío, mensaje saliente o inbox no permitida"
        }

    # El id del mensaje es estable entre reintentos; el delivery id es el
    # respaldo cuando Chatwoot no lo incluye.
    delivery_key = str(
        parsed.get("message_id")
        or request.headers.get("x-chatwoot-delivery")
        or ""
    )

    if delivery_key and not await is_first_delivery(delivery_key):
        logger.info(
            "entrega duplicada descartada delivery_key=%s conversation_id=%s",
            delivery_key,
            parsed["conversation_id"],
        )

        return {
            "ignored": True,
            "reason": "Entrega duplicada"
        }

    background_tasks.add_task(process_message, parsed)

    logger.info(
        "mensaje aceptado conversation_id=%s inbox_id=%s channel=%s",
        parsed["conversation_id"],
        parsed.get("inbox_id"),
        parsed.get("channel"),
    )

    return {
        "accepted": True,
        "conversation_id": parsed["conversation_id"],
        "inbox_id": parsed.get("inbox_id"),
        "channel": parsed.get("channel"),
    }
