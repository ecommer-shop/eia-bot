# EIA Bot - FastAPI + Chatwoot + eia-rag

Backend en **FastAPI** para conectar los mensajes que llegan a **Chatwoot** desde canales como **WhatsApp** y **Messenger** con el servicio unificado de IA/RAG (`eia-rag`). El bot recibe eventos de Chatwoot mediante webhook, consulta a eia-rag y publica la respuesta en la conversación.

## Estado actual

* Desplegado en Railway como servicio `eia-bot`.
* Integrado con Chatwoot mediante webhook global `message_created`.
* Compatible con bandejas de entrada de WhatsApp y Messenger desde Chatwoot.
* Responde usando eia-rag (gateway unificado de RAG + LLM).
* La memoria conversacional vive en eia-rag (Redis/Valkey), no en eia-bot.

## Arquitectura

```text
WhatsApp / Messenger
        ↓
Chatwoot
        ↓ webhook message_created
FastAPI /api/chatwoot-webhook
        ↓
eia-rag (POST /chat)
        ↓ clasifica intención + busca en Qdrant + genera respuesta
FastAPI envía respuesta vía API de Chatwoot
        ↓
Chatwoot responde al cliente
```

## Estructura principal

```text
app/
  api/
    routes.py                 # Rutas FastAPI
  core/
    config.py                 # Variables de entorno
  schemas/
    chat.py                   # RagRequest / RagResponse (contrato con eia-rag)
  services/
    ai_service.py             # Cliente async hacia eia-rag
    chatwoot_parser.py        # Parser de webhooks de Chatwoot
    chatwoot_service.py       # Envío de mensajes a Chatwoot (async)
    webhook_parser.py         # Parser para webhook directo Messenger/Meta
  main.py                     # App FastAPI
requirements.txt
```

## Endpoints

### `GET /api/hello`

Prueba rápida de salud de la API.

### `POST /api/chat`

Prueba directa de eia-rag.

```json
{
  "query": "Hola, prueba de conexión"
}
```

### `POST /api/chatwoot-webhook`

Endpoint principal para Chatwoot. Recibe eventos `message_created`, filtra mensajes entrantes, consulta eia-rag y responde en la misma conversación.

URL usada en Railway:

```text
https://eia-bot-production.up.railway.app/api/chatwoot-webhook
```

### `POST /api/webhook`

Endpoint para pruebas con webhook directo de Messenger/Meta.

## Variables de entorno

### Chatwoot

```env
CHATWOOT_BASE_URL=https://chat.ecommer.shop
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_API_ACCESS_TOKEN=...
```

### IA / RAG

```env
EIA_RAG_URL=http://localhost:8000
```

En producción (Railway), apuntar a la URL interna de eia-rag:

```env
EIA_RAG_URL=http://eia-rag.railway.internal:8000
```

### Filtro opcional por inbox

```env
CHATWOOT_ALLOWED_INBOX_IDS=2,4
```

Los IDs se obtienen desde la URL de configuración de cada inbox en Chatwoot:

```text
/app/accounts/1/settings/inboxes/ID
```

## Configuración en Chatwoot

1. Ir a `Ajustes → Integraciones → Webhooks`.
2. Crear un webhook con URL:

```text
https://eia-bot-production.up.railway.app/api/chatwoot-webhook
```

3. Marcar únicamente el evento:

```text
Mensaje creado / message_created
```

4. Verificar que las bandejas de WhatsApp y Messenger existan en:

```text
Ajustes → Entradas
```

## Despliegue en Railway

El proyecto usa Dockerfile y `railway.json`.

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Railway asigna automáticamente el puerto mediante la variable `PORT`.

## Probar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set EIA_RAG_URL=http://localhost:8000
uvicorn app.main:app --reload --port 8002
```

Luego abrir:

```text
http://127.0.0.1:8002/docs
```

> eia-rag debe estar corriendo en paralelo.

## Pruebas recomendadas

### Probar salud

```text
GET /api/hello
```

### Probar IA

```json
{
  "query": "Hola, prueba de conexión"
}
```

en:

```text
POST /api/chat
```

### Probar Chatwoot

1. Enviar un mensaje real desde WhatsApp o Messenger.
2. Revisar en Railway:

```text
eia-bot → Deployments → HTTP Logs
```

3. Si aparece `500`, revisar:

```text
eia-bot → Deployments → Deploy Logs
```

Buscar:

```text
=== ERROR CHATWOOT WEBHOOK ===
```

## Notas importantes

* Chatwoot guarda el historial real de conversaciones.
* La memoria conversacional vive en eia-rag (Redis/Valkey), no en eia-bot.
* El webhook debe escuchar `message_created`.
* Los mensajes salientes del bot deben ser ignorados por el parser para evitar bucles.
* Si Messenger no responde, revisar el `inbox_id` y la variable `CHATWOOT_ALLOWED_INBOX_IDS`.
* Si falla el envío a Chatwoot, revisar `CHATWOOT_API_ACCESS_TOKEN`, `CHATWOOT_ACCOUNT_ID` y `CHATWOOT_BASE_URL`.
