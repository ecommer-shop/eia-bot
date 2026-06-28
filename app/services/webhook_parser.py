def parse_messenger_webhook(payload: dict) -> dict | None:
    """
    Convierte el JSON del webhook de Messenger en:
    {
        "query": "...",
        "sender_id": "..."
    }

    Si el mensaje es echo o viene vacío, retorna None.
    """

    try:
        # Soporta dos casos:
        # 1. Payload directo de Meta: {"entry": [...]}
        # 2. Payload envuelto por n8n: {"body": {"entry": [...]}}
        body = payload.get("body", payload)

        msg = body["entry"][0]["messaging"][0]

        message = msg.get("message", {})
        es_echo = message.get("is_echo", False)

        if es_echo:
            return None

        mensaje = message.get("text", "").strip()

        if not mensaje:
            return None

        sender_id = msg["sender"]["id"]

        return {
            "query": mensaje,
            "sender_id": sender_id
        }

    except (KeyError, IndexError, TypeError):
        return None