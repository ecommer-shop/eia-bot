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


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [v.strip() for v in raw.split("|") if v.strip()]


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
    # El RAG usa un modelo con razonamiento (gpt-oss-120b): medido en vivo entre
    # 6s y 30s, así que 40s da margen sin abandonar respuestas que sí iban a
    # llegar — preferible a caer a Phi-4, que responde sin el contexto del RAG.
    ai_timeout_seconds: float = _float_env("AI_TIMEOUT_SECONDS", 40.0)
    chatwoot_timeout_seconds: float = _float_env("CHATWOOT_TIMEOUT_SECONDS", 15.0)

    # Ventana para descartar entregas repetidas del mismo mensaje.
    dedup_ttl_seconds: int = _int_env("DEDUP_TTL_SECONDS", 3600)

    # ─── Azure AI Foundry (Phi-4) ──────────────────────────────
    # Red de seguridad cuando el RAG falla o Groq esta caido/deprecado.
    # Sin estas variables el bot sigue funcionando, solo sin respaldo.
    azure_ai_endpoint: str | None = os.getenv("AZURE_AI_ENDPOINT")
    azure_ai_key: str | None = os.getenv("AZURE_AI_KEY")
    azure_ai_deployment: str = os.getenv("AZURE_AI_DEPLOYMENT", "Phi-4")

    default_system_prompt: str = os.getenv(
        "DEFAULT_SYSTEM_PROMPT",
        "Eres SimetrIA, el asistente virtual de ecommer, una plataforma "
        "marketplace para emprendimientos colombianos. Ayudas a los clientes "
        "con dudas frecuentes y preguntas sobre los productos de la tienda. "
        "Responde siempre en español, de forma amable y concisa. "
        "No inventes precios ni información que no tengas.",
    )

    # El RAG devuelve HTTP 200 aunque su LLM haya fallado: el aviso queda
    # dentro de 'answer'. Estos fragmentos (sin tildes, en minusculas) se
    # comparan de forma flexible para detectar esa respuesta degradada.
    rag_fallback_markers: list[str] = _list_env(
        "RAG_FALLBACK_MARKERS",
        ["problemas tecnicos en este momento", "no pude generar una respuesta"],
    )

    fallback_message: str = os.getenv(
        "FALLBACK_MESSAGE",
        "Disculpa, tuve un problema técnico procesando tu mensaje. "
        "¿Podrías intentarlo de nuevo en un momento?",
    )


settings = Settings()
