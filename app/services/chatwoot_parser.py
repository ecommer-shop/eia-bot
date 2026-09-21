import os


def normalize_chatwoot_channel(channel: str | None) -> str:
    channel_map = {
        "Channel::Whatsapp": "whatsapp",
        "Channel::Instagram": "instagram",
        "Channel::FacebookPage": "facebook",
        "Channel::WebWidget": "shop",
        "Channel::Api": "api",
    }

    return channel_map.get(channel, "unknown")


def parse_chatwoot_webhook(payload: dict) -> dict | None:
    try:
        body = payload.get("body", payload)

        event = body.get("event")
        message_type = body.get("message_type")
        private = body.get("private", False)

        print("DEBUG CHATWOOT EVENT:", event, flush=True)
        print("DEBUG CHATWOOT MESSAGE TYPE:", message_type, flush=True)
        print("DEBUG CHATWOOT PRIVATE:", private, flush=True)

        if event != "message_created":
            print("IGNORADO: event no es message_created", event, flush=True)
            return None

        if private is True:
            print("IGNORADO: mensaje privado", flush=True)
            return None

        if message_type not in ("incoming", 0, "0"):
            print("IGNORADO: message_type no es incoming", message_type, flush=True)
            return None

        content = (body.get("content") or "").strip()

        if not content:
            print("IGNORADO: content vacío", flush=True)
            return None

        conversation = body.get("conversation") or {}
        sender = body.get("sender") or {}
        inbox = body.get("inbox") or conversation.get("inbox") or {}
        account = body.get("account") or conversation.get("account") or {}

        conversation_id = (
            conversation.get("id")
            or body.get("conversation_id")
        )

        if not conversation_id:
            print("IGNORADO: conversation_id vacío", flush=True)
            return None

        account_id = (
            account.get("id")
            or body.get("account_id")
            or conversation.get("account_id")
        )

        inbox_id = (
            body.get("inbox_id")
            or conversation.get("inbox_id")
            or inbox.get("id")
        )

        channel = (
            conversation.get("channel")
            or body.get("channel")
            or inbox.get("channel_type")
        )

        canal = normalize_chatwoot_channel(channel)

        allowed_inboxes = os.getenv("CHATWOOT_ALLOWED_INBOX_IDS", "").strip()

        if allowed_inboxes and inbox_id is not None:
            allowed_ids = {
                int(value.strip())
                for value in allowed_inboxes.split(",")
                if value.strip().isdigit()
            }

            if int(inbox_id) not in allowed_ids:
                print("IGNORADO: inbox no permitido", inbox_id, flush=True)
                return None

        return {
            "query": content,
            "conversation_id": conversation_id,
            "sender_id": sender.get("id") if isinstance(sender, dict) else None,
            "message_id": body.get("id"),
            "account_id": account_id,
            "inbox_id": inbox_id,
            "channel": channel,
            "canal": canal,
        }

    except Exception as error:
        print("ERROR PARSEANDO CHATWOOT WEBHOOK:", str(error), flush=True)
        return None