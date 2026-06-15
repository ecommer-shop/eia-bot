"""
Configuración central — lee variables de entorno.
En Railway estas se definen en la pestaña Variables del servicio.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from functools import lru_cache


class Settings:
    # ─── Chatwoot ──────────────────────────────────────────────
    # URL base de tu instalación (sin slash final)
    CHATWOOT_BASE_URL: str = os.getenv(
        "CHATWOOT_BASE_URL",
        "https://chatwoot-production-fb30.up.railway.app",
    )
    # Token de acceso de tu perfil (Profile Settings → Access Token)
    CHATWOOT_API_TOKEN: str = os.getenv("CHATWOOT_API_TOKEN", "")
    # ID de la cuenta (normalmente 1)
    CHATWOOT_ACCOUNT_ID: str = os.getenv("CHATWOOT_ACCOUNT_ID", "1")

    # ─── Azure AI Foundry (Phi-4) ──────────────────────────────
    AZURE_AI_ENDPOINT: str = os.getenv("AZURE_AI_ENDPOINT", "")
    AZURE_AI_KEY: str = os.getenv("AZURE_AI_KEY", "")
    # Nombre del deployment de Phi-4 en Azure AI Foundry
    AZURE_AI_DEPLOYMENT: str = os.getenv("AZURE_AI_DEPLOYMENT", "phi-4")

    # ─── Postgres (memoria + estado) ───────────────────────────
    # Railway expone DATABASE_URL automáticamente al enlazar el servicio
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ─── RAG (simetria.ecommer.shop) ──────────────────────────
    # URL base del servicio RAG de ecommer (sin slash final)
    RAG_BASE_URL: str = os.getenv(
        "RAG_BASE_URL",
        "https://simetria.ecommer.shop",
    )

    # ─── Comportamiento del bot ────────────────────────────────
    # Palabras que activan el handoff a un humano
    HANDOFF_KEYWORDS = [
        "hablar con un humano", "hablar con alguien", "agente humano",
        "asesor", "persona real", "atención humana", "quiero hablar con",
    ]
    # System prompt por defecto (si el negocio no tiene uno propio)
    DEFAULT_SYSTEM_PROMPT: str = (
        "Eres SimetrIA, el asistente virtual de ecommer, una plataforma "
        "marketplace para emprendimientos colombianos. Ayudas a los clientes "
        "con dudas frecuentes y preguntas sobre los productos de la tienda. "
        "Responde siempre en español, de forma amable y concisa. "
        "Si no puedes resolver algo con certeza, ofrece conectar con un agente humano. "
        "No inventes precios ni información que no tengas."
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

