from app.services import ai_service, chatwoot_service
from app.services.chatwoot_parser import parse_chatwoot_webhook
from app.services.memory_service import get_memory_key


def payload(account_id=22, conversation_id=42, inbox_id=31, channel="Channel::Whatsapp"):
    return {
        "event": "message_created",
        "message_type": "incoming",
        "content": "Hola",
        "id": 9001,
        "account": {"id": account_id},
        "conversation": {"id": conversation_id, "channel": channel},
        "inbox": {"id": inbox_id},
        "sender": {"id": 7, "type": "contact"},
    }


def test_el_parser_extrae_la_cuenta():
    assert parse_chatwoot_webhook(payload(account_id=22))["account_id"] == 22


def test_la_memoria_no_se_mezcla_entre_cuentas_con_el_mismo_conversation_id():
    assert get_memory_key(42, 22) != get_memory_key(42, 5)


def test_normaliza_los_canales_de_chatwoot():
    assert ai_service.normalize_channel("Channel::Whatsapp") == "whatsapp"
    assert ai_service.normalize_channel("Channel::FacebookPage") == "messenger"
    assert ai_service.normalize_channel("Channel::Instagram") == "instagram"
    assert ai_service.normalize_channel(None) is None


def test_el_payload_al_rag_lleva_la_identidad_del_comercio():
    parsed = parse_chatwoot_webhook(payload(account_id=22, conversation_id=42, inbox_id=31))

    body = ai_service.build_rag_payload("Hola", parsed)

    assert body["query"] == "Hola"
    assert body["account_id"] == 22
    assert body["inbox_id"] == 31
    assert body["channel"] == "whatsapp"
    # el id de conversacion incluye la cuenta: se repite entre cuentas
    assert body["conversation_id"] == "22-42"


def test_sin_contexto_solo_se_envia_la_consulta():
    assert ai_service.build_rag_payload("Hola", None) == {"query": "Hola"}


async def test_responde_en_la_cuenta_de_la_conversacion(monkeypatch):
    llamadas = []

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": 1}

    class Cliente:
        async def post(self, url, **kwargs):
            llamadas.append(url)
            return Resp()

    monkeypatch.setattr(chatwoot_service, "get_client", lambda: Cliente())
    monkeypatch.setattr(chatwoot_service.settings, "chatwoot_base_url", "http://cw")
    monkeypatch.setattr(chatwoot_service.settings, "chatwoot_account_id", "1")

    await chatwoot_service.send_message_to_chatwoot(42, "hola", account_id=22)
    await chatwoot_service.send_message_to_chatwoot(42, "hola")

    assert llamadas[0] == "http://cw/api/v1/accounts/22/conversations/42/messages"
    # sin cuenta en el evento se usa la configurada por defecto
    assert llamadas[1] == "http://cw/api/v1/accounts/1/conversations/42/messages"
