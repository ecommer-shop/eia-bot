from app.services.chatwoot_parser import parse_chatwoot_webhook


def payload_base(**overrides):
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "content": "Hola, ¿tienen envíos a Medellín?",
        "id": 9001,
        "conversation": {"id": 42, "channel": "Channel::Whatsapp"},
        "inbox": {"id": 2},
        "sender": {"id": 77, "type": "contact"},
    }
    payload.update(overrides)
    return payload


def test_extrae_los_datos_de_un_mensaje_de_whatsapp():
    parsed = parse_chatwoot_webhook(payload_base())

    assert parsed["query"] == "Hola, ¿tienen envíos a Medellín?"
    assert parsed["conversation_id"] == 42
    assert parsed["message_id"] == 9001
    assert parsed["inbox_id"] == 2
    assert parsed["channel"] == "Channel::Whatsapp"


def test_reconoce_instagram_y_messenger():
    for channel in ("Channel::Instagram", "Channel::FacebookPage"):
        parsed = parse_chatwoot_webhook(
            payload_base(conversation={"id": 42, "channel": channel})
        )
        assert parsed["channel"] == channel


def test_ignora_eventos_que_no_son_mensajes_nuevos():
    assert parse_chatwoot_webhook(payload_base(event="conversation_updated")) is None


def test_ignora_mensajes_salientes_para_no_responderse_a_si_mismo():
    assert parse_chatwoot_webhook(payload_base(message_type="outgoing")) is None


def test_ignora_contenido_vacio_o_en_blanco():
    assert parse_chatwoot_webhook(payload_base(content="   ")) is None
    assert parse_chatwoot_webhook(payload_base(content=None)) is None


def test_ignora_mensajes_sin_conversacion():
    assert parse_chatwoot_webhook(payload_base(conversation={})) is None


def test_acepta_message_type_numerico():
    # Chatwoot usa 0 para incoming en algunas estructuras internas
    assert parse_chatwoot_webhook(payload_base(message_type=0)) is not None


def test_la_allowlist_descarta_inboxes_no_autorizadas(monkeypatch):
    monkeypatch.setenv("CHATWOOT_ALLOWED_INBOX_IDS", "4,7")

    assert parse_chatwoot_webhook(payload_base(inbox={"id": 2})) is None
    assert parse_chatwoot_webhook(payload_base(inbox={"id": 4})) is not None
