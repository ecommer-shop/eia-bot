"""El RAG responde HTTP 200 aunque su LLM haya fallado: el aviso queda
dentro de 'answer'. Estas pruebas cubren que ese caso, y los errores de
red, activen el respaldo con Phi-4 en vez de reenviar el aviso al cliente.
"""

import httpx
import pytest

from app.services import ai_service


class FakeResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, response: FakeResponse | None = None, exc: Exception | None = None):
        self._response = response
        self._exc = exc

    async def post(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


class FakePhi4Completions:
    def __init__(self, texto="respuesta de Phi-4"):
        self.texto = texto

    async def create(self, **kwargs):
        class Choice:
            message = type("M", (), {"content": self.texto})()

        class Resp:
            choices = [Choice()]

        return Resp()


class FakePhi4Client:
    def __init__(self, texto="respuesta de Phi-4"):
        self.chat = type("C", (), {"completions": FakePhi4Completions(texto)})()

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def _reset_phi4_singleton(monkeypatch):
    monkeypatch.setattr(ai_service, "_phi4", None)
    yield
    ai_service._phi4 = None


def test_detecta_la_respuesta_degradada_del_rag_sin_importar_tildes():
    con_acento = "Lo siento, estoy teniendo problemas técnicos en este momento para procesar tu solicitud."
    sin_acento = "lo siento, estoy teniendo problemas tecnicos en este momento..."

    assert ai_service.is_degraded_answer(con_acento) is True
    assert ai_service.is_degraded_answer(sin_acento) is True


def test_una_respuesta_normal_no_se_marca_como_degradada():
    assert ai_service.is_degraded_answer("Claro, hacemos envíos a toda Colombia.") is False


def test_una_respuesta_vacia_se_trata_como_degradada():
    assert ai_service.is_degraded_answer("") is True
    assert ai_service.is_degraded_answer("   ") is True


async def test_usa_la_respuesta_del_rag_cuando_es_valida(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "simetria_api_url", "http://test/chat")
    monkeypatch.setattr(
        ai_service,
        "get_client",
        lambda: FakeClient(FakeResponse(200, {"answer": "Sí, hacemos envíos."})),
    )

    respuesta = await ai_service.generate_reply("¿Hacen envíos?", [])

    assert respuesta == "Sí, hacemos envíos."


async def test_recurre_a_phi4_si_el_rag_responde_degradado(monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "get_client",
        lambda: FakeClient(FakeResponse(
            200,
            {"answer": "Lo siento, estoy teniendo problemas técnicos en este momento..."},
        )),
    )
    monkeypatch.setattr(ai_service, "_get_phi4", lambda: FakePhi4Client("desde Phi-4"))

    respuesta = await ai_service.generate_reply("hola", [])

    assert respuesta == "desde Phi-4"


async def test_recurre_a_phi4_si_el_rag_falla_por_red(monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "get_client",
        lambda: FakeClient(exc=httpx.ConnectError("timeout")),
    )
    monkeypatch.setattr(ai_service, "_get_phi4", lambda: FakePhi4Client("desde Phi-4"))

    respuesta = await ai_service.generate_reply("hola", [])

    assert respuesta == "desde Phi-4"


async def test_devuelve_mensaje_generico_si_ambos_fallan(monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "get_client",
        lambda: FakeClient(exc=httpx.ConnectError("timeout")),
    )
    monkeypatch.setattr(ai_service, "_get_phi4", lambda: None)

    respuesta = await ai_service.generate_reply("hola", [])

    assert respuesta == ai_service.settings.fallback_message
