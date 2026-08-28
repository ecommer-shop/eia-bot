import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def payload(message_id=9001, content="Hola, ¿hacen envíos?"):
    return {
        "event": "message_created",
        "message_type": "incoming",
        "content": content,
        "id": message_id,
        "conversation": {"id": 42, "channel": "Channel::Whatsapp"},
        "inbox": {"id": 2},
        "sender": {"id": 77, "type": "contact"},
    }


def test_acepta_el_mensaje_y_lo_procesa_en_segundo_plano(client, fake_redis, monkeypatch):
    llamadas = []

    async def spy(parsed):
        llamadas.append(parsed)

    monkeypatch.setattr("app.api.routes.process_message", spy)

    respuesta = client.post("/api/chatwoot-webhook", json=payload())

    assert respuesta.status_code == 200
    assert respuesta.json()["accepted"] is True
    assert len(llamadas) == 1
    assert llamadas[0]["conversation_id"] == 42


def test_descarta_la_segunda_entrega_del_mismo_mensaje(client, fake_redis, monkeypatch):
    llamadas = []

    async def spy(parsed):
        llamadas.append(parsed)

    monkeypatch.setattr("app.api.routes.process_message", spy)

    primera = client.post("/api/chatwoot-webhook", json=payload(message_id=555))
    segunda = client.post("/api/chatwoot-webhook", json=payload(message_id=555))

    assert primera.json()["accepted"] is True
    assert segunda.json()["ignored"] is True
    assert segunda.json()["reason"] == "Entrega duplicada"
    # El cliente debe recibir una sola respuesta, no una por reintento
    assert len(llamadas) == 1


def test_no_devuelve_500_aunque_falle_el_rag(client, fake_redis, monkeypatch):
    async def explota(user_message, history=None):
        raise RuntimeError("RAG caído")

    monkeypatch.setattr("app.services.conversation_service.generate_reply", explota)

    respuesta = client.post("/api/chatwoot-webhook", json=payload(message_id=777))

    # Un 500 haria que Chatwoot reintentara y duplicara la respuesta al cliente
    assert respuesta.status_code == 200


def test_ignora_un_cuerpo_que_no_es_json(client):
    respuesta = client.post(
        "/api/chatwoot-webhook",
        content="esto no es json",
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["ignored"] is True


def test_no_registra_el_contenido_del_mensaje(client, fake_redis, monkeypatch, caplog):
    async def spy(parsed):
        return None

    monkeypatch.setattr("app.api.routes.process_message", spy)

    secreto = "mi tarjeta es 4111111111111111"

    with caplog.at_level(logging.DEBUG):
        client.post("/api/chatwoot-webhook", json=payload(message_id=888, content=secreto))

    assert secreto not in caplog.text
