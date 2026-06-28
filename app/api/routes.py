from fastapi import APIRouter, HTTPException, Body

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import get_ai_response
from app.services.webhook_parser import parse_messenger_webhook
from app.services.chatwoot_parser import parse_chatwoot_webhook
from app.services.chatwoot_service import send_message_to_chatwoot
from app.services.memory_service import (
    get_conversation_memory,
    add_message_to_memory,
    build_context_prompt,
)

router = APIRouter(
    prefix="/api",
    tags=["API"]
)


def get_text_from_chat_request(request: ChatRequest) -> str:
    """
    Soporta distintos nombres de campo:
    - query
    - message
    - prompt
    """
    text = (
        getattr(request, "query", None)
        or getattr(request, "message", None)
        or getattr(request, "prompt", None)
    )

    if not text:
        raise ValueError("Debes enviar 'query', 'message' o 'prompt'")

    return text


@router.get("/hello")
def hello():
    return {
        "message": "Hola desde la API"
    }


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        query = get_text_from_chat_request(request)

        response = get_ai_response(query)

        return ChatResponse(
            response=response
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la API de Simetria: {str(error)}"
        )


@router.post("/webhook", summary="Messenger Webhook")
async def messenger_webhook(payload: dict = Body(...)):
    """
    Webhook directo de Messenger/Meta.

    Ojo:
    Este endpoint retorna la respuesta, pero Meta no envía automáticamente
    esa respuesta al usuario solo por devolver JSON.
    Para responder directo por Meta haría falta usar PAGE_ACCESS_TOKEN.

    Si Messenger entra por Chatwoot, usa /chatwoot-webhook.
    """
    parsed = parse_messenger_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Mensaje vacío, echo o formato inválido"
        }

    try:
        conversation_id = (
            parsed.get("conversation_id")
            or parsed.get("sender_id")
        )

        history = get_conversation_memory(conversation_id)

        prompt_with_context = build_context_prompt(
            history=history,
            current_message=parsed["query"]
        )

        ai_response = get_ai_response(prompt_with_context)

        add_message_to_memory(
            conversation_id=conversation_id,
            role="user",
            content=parsed["query"]
        )

        add_message_to_memory(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response
        )

        return {
            "ignored": False,
            "source": "messenger_direct",
            "sender_id": parsed.get("sender_id"),
            "query": parsed["query"],
            "response": ai_response
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
        conversation_id = parsed["conversation_id"]
        user_message = parsed["query"]

        history = get_conversation_memory(conversation_id)

        prompt_with_context = build_context_prompt(
            history=history,
            current_message=user_message
        )

        ai_response = get_ai_response(prompt_with_context)

        print("=== AI RESPONSE ===", flush=True)
        print(ai_response, flush=True)

        chatwoot_response = send_message_to_chatwoot(
            conversation_id=conversation_id,
            content=ai_response
        )

        print("=== CHATWOOT SEND RESPONSE ===", flush=True)
        print(chatwoot_response, flush=True)

        add_message_to_memory(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )

        add_message_to_memory(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response
        )

        return {
            "ignored": False,
            "source": "chatwoot",
            "conversation_id": conversation_id,
            "sender_id": parsed.get("sender_id"),
            "message_id": parsed.get("message_id"),
            "inbox_id": parsed.get("inbox_id"),
            "channel": parsed.get("channel"),
            "query": user_message,
            "response": ai_response,
            "chatwoot_message_id": chatwoot_response.get("id")
        }

    except Exception as error:
        print("=== ERROR CHATWOOT WEBHOOK ===", flush=True)
        print(str(error), flush=True)

        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook de Chatwoot: {str(error)}"
        )