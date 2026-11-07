import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    project_name: str = "Chatbot API"
    version: str = "0.1.0"

    simetria_api_url: str | None = (
        os.getenv("SIMETRIA_API_URL")
        or os.getenv("EIA_RAG_URL")
        or os.getenv("RAG_BASE_URL")
    )

    simetria_api_key: str | None = os.getenv("SIMETRIA_API_KEY")

    chatwoot_base_url: str | None = os.getenv("CHATWOOT_BASE_URL")

    chatwoot_account_id: str | None = os.getenv("CHATWOOT_ACCOUNT_ID")

    chatwoot_api_access_token: str | None = (
        os.getenv("CHATWOOT_API_ACCESS_TOKEN")
        or os.getenv("CHATWOOT_API_TOKEN")
    )

    valkey_url: str | None = os.getenv("VALKEY_URL") or os.getenv("REDIS_URL")

    # Verificación de peticiones entrantes. Vacías = sin verificar (despliegue gradual).
    # Secreto con el que Chatwoot firma sus webhooks (campo "secret" del webhook).
    chatwoot_webhook_secret: str | None = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    # Clave para los endpoints de prueba /api/chat y /api/webhook (cabecera X-API-Key).
    bot_api_key: str | None = os.getenv("BOT_API_KEY")


settings = Settings()