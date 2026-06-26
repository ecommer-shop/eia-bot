from fastapi import APIRouter, HTTPException, Body

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import get_ai_response
from app.services.webhook_parser import parse_messenger_webhook
from app.services.chatwoot_parser import parse_chatwoot_webhook

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
def chat(request: ChatRequest):
    try:
        response = get_ai_response(request.prompt)

        return ChatResponse(
            response=response
        )

    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la API de Simetria: {str(error)}"
        )


@router.post("/webhook", summary="Messenger Webhook")
async def messenger_webhook(payload: dict = Body(...)):
    parsed = parse_messenger_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Mensaje vacío, echo o formato inválido"
        }

    try:
        response = get_ai_response(parsed["query"])

        return {
            "ignored": False,
            "sender_id": parsed["sender_id"],
            "query": parsed["query"],
            "response": response
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {str(error)}"
        )


@router.post("/chatwoot-webhook", summary="Chatwoot Webhook")
async def chatwoot_webhook(payload: dict = Body(...)):
    parsed = parse_chatwoot_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Evento no válido, mensaje vacío o mensaje saliente"
        }

    try:
        response = get_ai_response(parsed["query"])

        return {
            "ignored": False,
            "source": "chatwoot",
            "conversation_id": parsed["conversation_id"],
            "sender_id": parsed["sender_id"],
            "message_id": parsed["message_id"],
            "query": parsed["query"],
            "response": response
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook de Chatwoot: {str(error)}"
        )