import pytest
from fastapi.testclient import TestClient

from app.api import onboarding as onboarding_api
from app.main import app
from app.services import onboarding_service

TOKEN = "t" * 32


@pytest.fixture
def client(monkeypatch):
    settings = onboarding_api.settings
    monkeypatch.setattr(settings, "onboarding_admin_token", TOKEN)
    monkeypatch.setattr(settings, "meta_app_id", "111222333")
    monkeypatch.setattr(settings, "meta_config_id", "444555666")
    monkeypatch.setattr(settings, "meta_api_version", "v25.0")

    cw = onboarding_service.settings
    monkeypatch.setattr(cw, "chatwoot_base_url", "http://cw")
    monkeypatch.setattr(cw, "chatwoot_api_access_token", "service-token")

    return TestClient(app)


def body(**overrides):
    data = {
        "account_id": 22,
        "code": "AQB-codigo",
        "waba_id": "1234567890",
        "business_id": "9876543210",
        "phone_number_id": "5555555555",
        "is_coexistence": False,
    }
    data.update(overrides)
    return data


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("sin json")
        return self._payload


def fake_chatwoot(monkeypatch, response):
    llamadas = []

    class Cliente:
        async def post(self, url, **kwargs):
            llamadas.append({"url": url, **kwargs})
            return response

    monkeypatch.setattr(onboarding_service, "get_client", lambda: Cliente())
    return llamadas


def test_la_pagina_lleva_los_ids_de_meta_y_no_expone_la_clave(client):
    respuesta = client.get("/onboarding")

    assert respuesta.status_code == 200
    assert 'data-app-id="111222333"' in respuesta.text
    assert 'data-config-id="444555666"' in respuesta.text
    assert TOKEN not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["x-frame-options"] == "DENY"


def test_sin_configurar_queda_apagado(client, monkeypatch):
    monkeypatch.setattr(onboarding_api.settings, "onboarding_admin_token", None)

    assert client.get("/onboarding").status_code == 503
    assert client.post("/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": TOKEN}).status_code == 503


def test_una_clave_corta_se_trata_como_no_configurada(client, monkeypatch):
    monkeypatch.setattr(onboarding_api.settings, "onboarding_admin_token", "corta")

    assert client.get("/onboarding").status_code == 503


def test_rechaza_una_clave_incorrecta_o_ausente(client):
    sin_clave = client.post("/onboarding/whatsapp", json=body())
    mala = client.post("/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": "x" * 32})

    assert sin_clave.status_code == 401
    assert mala.status_code == 401


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("account_id", 0),
        ("account_id", "22/../1"),
        ("waba_id", "abc"),
        ("waba_id", "123; drop"),
        ("business_id", "no-numerico"),
        ("code", ""),
    ],
)
def test_valida_los_datos_antes_de_llamar_a_chatwoot(client, monkeypatch, campo, valor):
    llamadas = fake_chatwoot(monkeypatch, FakeResponse(200, {"success": True}))

    respuesta = client.post(
        "/onboarding/whatsapp",
        json=body(**{campo: valor}),
        headers={"X-Onboarding-Token": TOKEN},
    )

    assert respuesta.status_code == 422
    assert llamadas == []


def test_el_alta_llega_a_la_cuenta_correcta_de_chatwoot(client, monkeypatch):
    llamadas = fake_chatwoot(
        monkeypatch, FakeResponse(200, {"success": True, "id": 31, "name": "Tienda WhatsApp"})
    )

    respuesta = client.post(
        "/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": TOKEN}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True, "inbox_id": 31, "inbox_name": "Tienda WhatsApp"}

    llamada = llamadas[0]
    assert llamada["url"] == "http://cw/api/v1/accounts/22/whatsapp/authorization"
    assert llamada["headers"]["api_access_token"] == "service-token"
    assert llamada["json"] == {
        "code": "AQB-codigo",
        "waba_id": "1234567890",
        "business_id": "9876543210",
        "phone_number_id": "5555555555",
    }


def test_la_coexistencia_sin_business_id_envia_solo_lo_que_meta_entrega(client, monkeypatch):
    llamadas = fake_chatwoot(monkeypatch, FakeResponse(200, {"success": True, "id": 7, "name": "X"}))

    client.post(
        "/onboarding/whatsapp",
        json=body(business_id=None, phone_number_id=None, is_coexistence=True),
        headers={"X-Onboarding-Token": TOKEN},
    )

    assert llamadas[0]["json"] == {
        "code": "AQB-codigo",
        "waba_id": "1234567890",
        "is_coexistence": True,
    }


def test_sin_acceso_a_la_cuenta_explica_que_el_usuario_de_servicio_debe_ser_admin(client, monkeypatch):
    fake_chatwoot(monkeypatch, FakeResponse(401, {}))

    respuesta = client.post("/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": TOKEN})

    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"]


def test_muestra_el_error_de_chatwoot_sin_inventar_exito(client, monkeypatch):
    fake_chatwoot(
        monkeypatch,
        FakeResponse(422, {"success": False, "error": "Required parameters are missing: business_id"}),
    )

    respuesta = client.post("/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": TOKEN})

    assert respuesta.status_code == 422
    assert "business_id" in respuesta.json()["detail"]


def test_no_registra_el_codigo_ni_el_token(client, monkeypatch, caplog):
    import logging

    fake_chatwoot(monkeypatch, FakeResponse(200, {"success": True, "id": 1, "name": "X"}))

    with caplog.at_level(logging.DEBUG):
        client.post("/onboarding/whatsapp", json=body(), headers={"X-Onboarding-Token": TOKEN})

    assert "AQB-codigo" not in caplog.text
    assert TOKEN not in caplog.text
    assert "service-token" not in caplog.text


def test_el_script_se_sirve_y_espera_a_fbasyncinit(client):
    respuesta = client.get("/onboarding/static/onboarding.js")

    assert respuesta.status_code == 200
    assert "window.fbAsyncInit" in respuesta.text
    # el boton se habilita solo desde fbAsyncInit, no por la existencia de window.FB
    assert "if (window.FB)" not in respuesta.text
