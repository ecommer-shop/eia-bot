"""Verificación opcional de firma de Chatwoot y de la clave de los endpoints de prueba.

Ejecutar sin tocar pyproject: `uv run --with pytest python -m pytest tests`
"""
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

SECRETO = "secreto-de-prueba-no-real"
CLAVE = "clave-de-prueba-no-real"
# Evento que el parser descarta: la petición autenticada termina en 200 sin llamar a servicios externos.
CUERPO = json.dumps({"event": "message_updated"}).encode()


@pytest.fixture
def client():
    return TestClient(app)


def firmar(cuerpo: bytes, ts: int | str, secreto: str = SECRETO) -> dict:
    firma = hmac.new(secreto.encode(), f"{ts}.".encode() + cuerpo, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Chatwoot-Timestamp": str(ts),
        "X-Chatwoot-Signature": f"sha256={firma}",
    }


def post_webhook(client, cabeceras):
    return client.post("/api/chatwoot-webhook", content=CUERPO, headers=cabeceras)


class TestFirmaChatwoot:
    def test_sin_secreto_configurado_no_verifica(self, client, monkeypatch):
        monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
        r = post_webhook(client, {"Content-Type": "application/json"})
        assert r.status_code == 200

    def test_firma_valida_pasa(self, client, monkeypatch):
        monkeypatch.setattr(settings, "chatwoot_webhook_secret", SECRETO)
        r = post_webhook(client, firmar(CUERPO, int(time.time())))
        assert r.status_code == 200
        assert r.json()["ignored"] is True

    @pytest.mark.parametrize(
        "caso",
        ["sin_cabeceras", "firma_de_otro_secreto", "cuerpo_alterado", "timestamp_viejo", "timestamp_no_numerico"],
    )
    def test_rechaza(self, client, monkeypatch, caso):
        monkeypatch.setattr(settings, "chatwoot_webhook_secret", SECRETO)
        ahora = int(time.time())
        if caso == "sin_cabeceras":
            cabeceras = {"Content-Type": "application/json"}
        elif caso == "firma_de_otro_secreto":
            cabeceras = firmar(CUERPO, ahora, secreto="otro")
        elif caso == "cuerpo_alterado":
            cabeceras = firmar(CUERPO + b" ", ahora)  # firma de otro cuerpo
        elif caso == "timestamp_viejo":
            cabeceras = firmar(CUERPO, ahora - 3600)
        else:
            cabeceras = firmar(CUERPO, "abc")
        r = post_webhook(client, cabeceras)
        assert r.status_code == 401
        assert r.json() == {"detail": "No autorizado"}


@pytest.mark.parametrize("ruta", ["/api/chat", "/api/webhook"])
class TestClaveEndpointsDePrueba:
    def test_sin_clave_configurada_no_exige(self, client, monkeypatch, ruta):
        monkeypatch.setattr(settings, "bot_api_key", None)
        assert client.post(ruta, json={}).status_code != 401

    @pytest.mark.parametrize("cabeceras", [{}, {"X-API-Key": ""}, {"X-API-Key": "incorrecta"}])
    def test_con_clave_rechaza_ausente_o_incorrecta(self, client, monkeypatch, ruta, cabeceras):
        monkeypatch.setattr(settings, "bot_api_key", CLAVE)
        r = client.post(ruta, json={}, headers=cabeceras)
        assert r.status_code == 401

    def test_con_clave_correcta_pasa(self, client, monkeypatch, ruta):
        monkeypatch.setattr(settings, "bot_api_key", CLAVE)
        assert client.post(ruta, json={}, headers={"X-API-Key": CLAVE}).status_code != 401


def test_health_sigue_abierto(client, monkeypatch):
    monkeypatch.setattr(settings, "bot_api_key", CLAVE)
    monkeypatch.setattr(settings, "chatwoot_webhook_secret", SECRETO)
    assert client.get("/health").status_code == 200
