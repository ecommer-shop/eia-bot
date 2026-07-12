from fastapi import APIRouter, HTTPException, Body

from app.services.ai_service import call_eia_rag
from app.services.webhook_parser import parse_messenger_webhook
from app.services.chatwoot_parser import parse_chatwoot_webhook
from app.services.chatwoot_service import send_message_to_chatwoot

router = APIRouter(
    prefix="/api",
    tags=["API"]
)


@router.get("/hello")
def hello():
    return {
        "message": "Hola desde la API"
    }


@router.post("/chat")
async def chat(payload: dict = Body(...)):
    try:
        query = payload.get("query") or payload.get("message") or payload.get("prompt")

        if not query:
            raise ValueError("Debes enviar 'query', 'message' o 'prompt'")

        result = await call_eia_rag(
            query=query,
            conversation_id=payload.get("conversation_id", "test"),
            inbox_id=payload.get("inbox_id", 0),
            user_id=payload.get("user_id"),
            channel=payload.get("channel"),
        )

        return {"answer": result.answer}

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar eia-rag: {str(error)}"
        )


@router.post("/webhook", summary="Messenger Webhook")
async def messenger_webhook(payload: dict = Body(...)):
    """
    Webhook directo de Messenger/Meta.

    Este endpoint sirve para simular/probar Messenger desde Swagger.
    Para producción real con Chatwoot, lo recomendado es usar /chatwoot-webhook.
    """

    parsed = parse_messenger_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Mensaje vacío, echo o formato inválido"
        }

    try:
        conversation_id = str(
            parsed.get("conversation_id")
            or parsed.get("sender_id")
        )

        user_message = parsed["query"]

        result = await call_eia_rag(
            query=user_message,
            conversation_id=conversation_id,
            inbox_id=0,
            user_id=parsed.get("sender_id"),
        )

        return {
            "ignored": False,
            "source": "messenger_direct",
            "sender_id": parsed.get("sender_id"),
            "query": user_message,
            "response": result.answer
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {str(error)}"
        )


@router.post("/chatwoot-webhook", summary="Chatwoot Webhook")
async def chatwoot_webhook(payload: dict = Body(...)):
    print("=== CHATWOOT WEBHOOK PAYLOAD ===", flush=True)
    print(payload, flush=True)

    parsed = parse_chatwoot_webhook(payload)

    print("=== CHATWOOT PARSED ===", flush=True)
    print(parsed, flush=True)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Evento no válido, mensaje vacío, mensaje saliente o inbox no permitida"
        }

    try:
        user_message = parsed["query"]

        result = await call_eia_rag(
            query=user_message,
            conversation_id=f"chatwoot_{parsed['conversation_id']}",
            inbox_id=parsed["inbox_id"],
            user_id=parsed.get("sender_id"),
            channel=parsed.get("channel"),
        )

        print("=== AI RESPONSE ===", flush=True)
        print(result.answer, flush=True)

        chatwoot_response = await send_message_to_chatwoot(
            conversation_id=parsed["conversation_id"],
            content=result.answer
        )

        print("=== CHATWOOT SEND RESPONSE ===", flush=True)
        print(chatwoot_response, flush=True)

        return {
            "ignored": False,
            "source": "chatwoot",
            "conversation_id": parsed["conversation_id"],
            "sender_id": parsed.get("sender_id"),
            "message_id": parsed.get("message_id"),
            "inbox_id": parsed.get("inbox_id"),
            "channel": parsed.get("channel"),
            "query": user_message,
            "response": result.answer,
            "chatwoot_message_id": chatwoot_response.get("id")
        }

    except Exception as error:
        print("=== ERROR CHATWOOT WEBHOOK ===", flush=True)
        print(str(error), flush=True)

        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook de Chatwoot: {str(error)}"
        )