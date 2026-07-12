import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    project_name: str = "Chatbot API"
    version: str = "0.1.0"

    # Chatwoot
    chatwoot_base_url: str | None = os.getenv("CHATWOOT_BASE_URL")
    chatwoot_account_id: str | None = os.getenv("CHATWOOT_ACCOUNT_ID")
    chatwoot_api_access_token: str | None = os.getenv("CHATWOOT_API_ACCESS_TOKEN")
    chatwoot_allowed_inbox_ids: str | None = os.getenv("CHATWOOT_ALLOWED_INBOX_IDS")

    # IA — eia-rag unificado
    eia_rag_url: str = os.getenv("EIA_RAG_URL", "http://localhost:8000")


settings = Settings()