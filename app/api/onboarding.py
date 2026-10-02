import hmac
import html
import logging
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.onboarding_service import OnboardingError, authorize_whatsapp

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Una clave corta se puede adivinar: se trata como "no configurada".
MIN_TOKEN_LENGTH = 24

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class OnboardingRequest(BaseModel):
    account_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=2000)
    waba_id: str = Field(pattern=r"^\d{5,30}$")
    business_id: str | None = Field(default=None, pattern=r"^\d{5,30}$")
    phone_number_id: str | None = Field(default=None, pattern=r"^\d{5,30}$")
    is_coexistence: bool = False


def _enabled() -> bool:
    return bool(
        settings.onboarding_admin_token
        and len(settings.onboarding_admin_token) >= MIN_TOKEN_LENGTH
        and settings.meta_app_id
        and settings.meta_config_id
    )


def _check_token(provided: str | None) -> None:
    expected = settings.onboarding_admin_token or ""
    if not hmac.compare_digest((provided or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Clave de onboarding incorrecta.")


@router.get("", response_class=HTMLResponse)
async def onboarding_page():
    if not _enabled():
        raise HTTPException(status_code=503, detail="El onboarding no está configurado.")

    page = (STATIC_DIR / "onboarding.html").read_text(encoding="utf-8")
    page = (
        page.replace("{{APP_ID}}", html.escape(settings.meta_app_id, quote=True))
        .replace("{{CONFIG_ID}}", html.escape(settings.meta_config_id, quote=True))
        .replace("{{VERSION}}", html.escape(settings.meta_api_version, quote=True))
    )

    return HTMLResponse(page, headers=_SECURITY_HEADERS)


@router.get("/static/onboarding.js")
async def onboarding_script():
    return FileResponse(
        STATIC_DIR / "onboarding.js",
        media_type="application/javascript",
        headers=_SECURITY_HEADERS,
    )


@router.post("/whatsapp")
async def onboard_whatsapp(
    request: OnboardingRequest,
    x_onboarding_token: str | None = Header(default=None),
):
    if not _enabled():
        raise HTTPException(status_code=503, detail="El onboarding no está configurado.")

    _check_token(x_onboarding_token)

    try:
        return await authorize_whatsapp(
            account_id=request.account_id,
            code=request.code,
            waba_id=request.waba_id,
            business_id=request.business_id,
            phone_number_id=request.phone_number_id,
            is_coexistence=request.is_coexistence,
        )
    except OnboardingError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    except Exception:
        logger.exception("fallo inesperado en el alta de WhatsApp")
        raise HTTPException(status_code=502, detail="No se pudo contactar a Chatwoot.")
