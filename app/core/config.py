import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    project_name: str = "Chatbot API"
    version: str = "0.1.0"

    simetria_api_url: str | None = os.getenv("SIMETRIA_API_URL")
    simetria_api_key: str | None = os.getenv("SIMETRIA_API_KEY")

    chatwoot_base_url: str | None = os.getenv("CHATWOOT_BASE_URL")
    chatwoot_account_id: str | None = os.getenv("CHATWOOT_ACCOUNT_ID")
    chatwoot_api_access_token: str | None = os.getenv("CHATWOOT_API_ACCESS_TOKEN")


settings = Settings()