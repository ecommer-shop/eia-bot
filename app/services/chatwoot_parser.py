import os


def parse_chatwoot_webhook(payload: dict) -> dict | None:
    try:
        event = payload.get("event")

        if event != "message_created":
            return None

        message_type = payload.get("message_type")

        # Chatwoot normalmente manda "incoming", pero a veces puede venir como 0
        if message_type not in ("incoming", 0):
            return None

        content = (payload.get("content") or "").strip()

        if not content:
            return None

        conversation = payload.get("conversation") or {}
        sender = payload.get("sender") or {}

        conversation_id = (
            conversation.get("id")
            or payload.get("conversation_id")
        )

        if not conversation_id:
            return None

        inbox_id = (
            payload.get("inbox_id")
            or conversation.get("inbox_id")
            or (payload.get("inbox") or {}).get("id")
            or (conversation.get("inbox") or {}).get("id")
        )

        allowed_inboxes = os.getenv("CHATWOOT_ALLOWED_INBOX_IDS", "").strip()

        if allowed_inboxes and inbox_id is not None:
            allowed_ids = {
                int(value.strip())
                for value in allowed_inboxes.split(",")
                if value.strip().isdigit()
            }

            if int(inbox_id) not in allowed_ids:
                return None

        return {
            "query": content,
            "conversation_id": conversation_id,
            "sender_id": sender.get("id"),
            "message_id": payload.get("id"),
            "inbox_id": inbox_id,
        }

    except Exception as error:
        print("ERROR PARSEANDO CHATWOOT WEBHOOK:", str(error))
        return None