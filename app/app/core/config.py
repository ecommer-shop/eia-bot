import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    project_name: str = "Chatbot API"
    version: str = "0.1.0"

    simetria_api_url: str | None = os.getenv("SIMETRIA_API_URL")
    simetria_api_key: str | None = os.getenv("SIMETRIA_API_KEY")


settings = Settings()