import os

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name) or default)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return default


class Settings:
    project_name: str = "Chatbot API"
    version: str = "0.1.0"

    simetria_api_url: str | None = os.getenv("SIMETRIA_API_URL")
    simetria_api_key: str | None = os.getenv("SIMETRIA_API_KEY")

    chatwoot_base_url: str | None = os.getenv("CHATWOOT_BASE_URL")
    chatwoot_account_id: str | None = os.getenv("CHATWOOT_ACCOUNT_ID")
    chatwoot_api_access_token: str | None = os.getenv("CHATWOOT_API_ACCESS_TOKEN")

    valkey_url: str | None = os.getenv("VALKEY_URL") or os.getenv("REDIS_URL")

    log_level: str = (os.getenv("LOG_LEVEL") or "INFO").upper()

    # Chatwoot corta el webhook a los 5s (WEBHOOK_TIMEOUT) y, si falla, abre la
    # conversacion a un agente humano. El trabajo pesado corre en segundo plano,
    # asi que estos timeouts ya no afectan el tiempo de respuesta del webhook.
    ai_timeout_seconds: float = _float_env("AI_TIMEOUT_SECONDS", 25.0)
    chatwoot_timeout_seconds: float = _float_env("CHATWOOT_TIMEOUT_SECONDS", 15.0)

    # Ventana para descartar entregas repetidas del mismo mensaje.
    dedup_ttl_seconds: int = _int_env("DEDUP_TTL_SECONDS", 3600)


settings = Settings()
