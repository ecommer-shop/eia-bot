"""Alta de un numero de WhatsApp en la cuenta de Chatwoot de un comercio.

El boton de Embedded Signup del dashboard de Chatwoot falla en todas las
versiones publicadas (FB.login se llama antes de que el SDK real este listo),
pero su API si funciona. La pagina de onboarding obtiene el codigo de Meta y
Chatwoot hace el resto: intercambia el codigo por el business token, crea la
bandeja, suscribe la app al WABA y registra el webhook del numero.
"""

import logging

from app.core.config import settings
from app.core.http import get_client

logger = logging.getLogger(__name__)

# Chatwoot intercambia el codigo, consulta el numero y registra webhooks en la
# misma peticion; el timeout normal de 15s se queda corto.
ONBOARDING_TIMEOUT_SECONDS = 60.0


class OnboardingError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


async def authorize_whatsapp(
    account_id: int,
    code: str,
    waba_id: str,
    business_id: str | None = None,
    phone_number_id: str | None = None,
    is_coexistence: bool = False,
) -> dict:
    if not settings.chatwoot_base_url or not settings.chatwoot_api_access_token:
        raise OnboardingError("Falta configurar Chatwoot en el servidor.", 503)

    url = (
        f"{settings.chatwoot_base_url}/api/v1/accounts/"
        f"{account_id}/whatsapp/authorization"
    )

    body: dict = {"code": code, "waba_id": waba_id}

    if _clean(business_id):
        body["business_id"] = business_id
    if _clean(phone_number_id):
        body["phone_number_id"] = phone_number_id
    if is_coexistence:
        body["is_coexistence"] = True

    # No se registra el codigo ni el token: son credenciales de un solo uso.
    logger.info(
        "alta de WhatsApp account_id=%s waba_id=%s coexistencia=%s",
        account_id,
        waba_id,
        is_coexistence,
    )

    response = await get_client().post(
        url,
        json=body,
        headers={
            "api_access_token": settings.chatwoot_api_access_token,
            "Content-Type": "application/json",
        },
        timeout=ONBOARDING_TIMEOUT_SECONDS,
    )

    if response.status_code in (401, 403, 404):
        raise OnboardingError(
            f"El usuario de servicio no tiene acceso a la cuenta {account_id}. "
            "Debe ser administrador de esa cuenta.",
            403,
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400 or not data.get("success"):
        detail = str(data.get("error") or data.get("message") or "Chatwoot rechazó el alta.")
        logger.warning(
            "Chatwoot rechazo el alta account_id=%s status=%s detalle=%s",
            account_id,
            response.status_code,
            detail[:300],
        )
        raise OnboardingError(detail[:300], 422)

    return {
        "success": True,
        "inbox_id": data.get("id"),
        "inbox_name": data.get("name"),
    }
