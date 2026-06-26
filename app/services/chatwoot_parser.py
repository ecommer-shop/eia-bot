import os


def parse_chatwoot_webhook(payload: dict) -> dict | None:
    try:
        event = payload.get("event")

        if event != "message_created":
            return None

        message_type = payload.get("message_type")

        if message_type != "incoming":
            return None

        content = payload.get("content", "").strip()

        if not content:
            return None

        conversation = payload.get("conversation", {})
        sender = payload.get("sender", {})
        inbox = payload.get("inbox") or conversation.get("inbox") or {}

        inbox_id = inbox.get("id")

        allowed_inboxes = os.getenv("CHATWOOT_ALLOWED_INBOX_IDS", "").strip()

        if allowed_inboxes:
            allowed_ids = {
                int(value.strip())
                for value in allowed_inboxes.split(",")
                if value.strip().isdigit()
            }

            if inbox_id not in allowed_ids:
                return None

        return {
            "query": content,
            "conversation_id": conversation.get("id"),
            "sender_id": sender.get("id"),
            "message_id": payload.get("id"),
            "inbox_id": inbox_id,
        }

    except (KeyError, TypeError, AttributeError, ValueError):
        return None