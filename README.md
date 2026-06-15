# ecommer WhatsApp Bot (FastAPI + Phi-4 + Chatwoot)

Backend que conecta WhatsApp Cloud API con un agente de IA (Azure Phi-4),
usando Chatwoot como bandeja de entrada y para el handoff humano.

## Arquitectura

```
WhatsApp -> Meta Cloud API -> Chatwoot -> Agent Bot -> FastAPI -> Phi-4
                                  ^                         |
                                  +---- responde via API ---+
```

Chatwoot es la fuente de verdad. El bot responde a traves de la API de
Chatwoot; cuando un cliente pide un humano (o un agente toma la conversacion),
el bot se pausa para esa conversacion.

## Estructura

- `app/main.py` — FastAPI + endpoints webhook
- `app/config.py` — variables de entorno
- `app/schemas/webhook.py` — validacion Pydantic del payload de Chatwoot
- `app/services/ai_agent.py` — cliente Azure Phi-4
- `app/services/chatwoot.py` — cliente API Chatwoot
- `app/services/conversation.py` — orquestador (handoff + memoria + IA)
- `app/models/database.py` — Postgres (memoria + estado handoff)

## Desplegar en Railway

1. Sube este repo a GitHub.
2. En Railway: New -> Deploy from GitHub repo.
3. Enlaza el servicio Postgres existente (Variables -> Reference -> DATABASE_URL).
4. Agrega las variables del archivo `.env.example`.
5. Railway construye con el Dockerfile y expone una URL publica.

## Conectar con Chatwoot

1. Super Admin -> Agent Bots -> crea uno con Outgoing URL:
   `https://TU-APP.up.railway.app/webhook/chatwoot`
2. Settings -> Inboxes -> tu inbox WhatsApp -> Configuration ->
   asigna el Agent Bot.
3. (Opcional) Settings -> Integrations -> Webhooks -> agrega
   `https://TU-APP.up.railway.app/webhook/chatwoot/status`
   con el evento `conversation_resolved` para reactivar el bot al cerrar.

## Probar local

```bash
pip install -r requirements.txt
cp .env.example .env   # y completa los valores
uvicorn app.main:app --reload
```
