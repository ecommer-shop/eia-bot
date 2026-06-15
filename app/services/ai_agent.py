"""
Servicio del AI Agent — llama al RAG (simetria.ecommer.shop).

El RAG de ecommer (eia-chat) expone POST /chat que recibe la pregunta
del cliente, busca contexto en los documentos de ecommer (Azure AI Search
+ Qdrant) y genera la respuesta con Groq (Llama 3). Nosotros lo consumimos
como una caja negra — le mandamos la pregunta, él devuelve la respuesta.

Si el RAG no responde, hacemos fallback a Azure Phi-4 directamente
para no dejar al cliente sin respuesta.
"""
import httpx
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

# Cliente Phi-4 solo para fallback
_phi4_client = AsyncOpenAI(
    base_url=settings.AZURE_AI_ENDPOINT,
    api_key=settings.AZURE_AI_KEY,
)


async def generate_reply(
    system_prompt: str,
    history: list,
    user_message: str,
) -> str:
    """
    Genera la respuesta del bot.
    1. Intenta el RAG (simetria.ecommer.shop/chat) — responde con contexto real
    2. Si falla, usa Phi-4 directamente como fallback
    """
    # ── Paso 1: intentar el RAG ──────────────────────────────────────────
    rag_url = settings.RAG_BASE_URL
    if rag_url:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"{rag_url}/chat",
                    json={"query": user_message},
                )
                resp.raise_for_status()
                data = resp.json()

                # El RAG puede devolver la respuesta en diferentes campos
                # según cómo esté implementado el endpoint /chat
                answer = (
                    data.get("answer")
                    or data.get("response")
                    or data.get("message")
                    or data.get("content")
                    or ""
                )
                if answer.strip():
                    return answer.strip()

        except Exception as e:
            print(f"[ai_agent] RAG no disponible, usando Phi-4: {e}")

    # ── Paso 2: fallback a Phi-4 ─────────────────────────────────────────
    if not settings.AZURE_AI_ENDPOINT or not settings.AZURE_AI_KEY:
        return (
            "Disculpa, tuve un problema técnico procesando tu mensaje. "
            "¿Podrías intentarlo de nuevo en un momento?"
        )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        resp = await _phi4_client.chat.completions.create(
            model=settings.AZURE_AI_DEPLOYMENT,
            messages=messages,
            temperature=0.4,
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ai_agent] Error en fallback Phi-4: {e}")
        return (
            "Disculpa, tuve un problema técnico procesando tu mensaje. "
            "¿Podrías intentarlo de nuevo en un momento?"
        )
