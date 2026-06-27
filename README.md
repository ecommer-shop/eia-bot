# EIA Bot - FastAPI + Chatwoot + IA/RAG

Backend en **FastAPI** para conectar los mensajes que llegan a **Chatwoot** desde canales como **WhatsApp** y **Messenger** con un servicio de IA/RAG. El bot recibe eventos de Chatwoot mediante webhook, genera una respuesta con IA y la publica nuevamente en la conversación usando la API de Chatwoot.

## Estado actual

* Desplegado en Railway como servicio `eia-bot`.
* Integrado con Chatwoot mediante webhook global `message_created`.
* Compatible con bandejas de entrada de WhatsApp y Messenger desde Chatwoot.
* Responde usando el servicio de IA configurado por variables de entorno.
* Puede usar Valkey/Redis como memoria temporal de conversación.

## Arquitectura

```text
WhatsApp / Messenger
        ↓
Chatwoot
        ↓ webhook message_created
FastAPI /api/chatwoot-webhook
        ↓
IA / RAG / Simetria / Azure
        ↓
FastAPI envía respuesta vía API de Chatwoot
        ↓
Chatwoot responde al cliente
```

Chatwoot sigue siendo la fuente principal del historial real de conversaciones. La memoria en Valkey, cuando se configura, solo se usa como contexto temporal para que la IA recuerde los últimos mensajes de una conversación.

## Estructura principal

```text
app/
  api/
    routes.py                 # Rutas FastAPI
  core/
    config.py                 # Variables de entorno
  schemas/
    chat.py                   # Esquemas de request/response
  services/
    ai_service.py             # Cliente hacia IA/RAG
    chatwoot_parser.py        # Parser de webhooks de Chatwoot
    chatwoot_service.py       # Envío de mensajes a Chatwoot
    memory_service.py         # Memoria temporal con Valkey/Redis
    webhook_parser.py         # Parser para webhook directo Messenger/Meta
  main.py                     # App FastAPI
Dockerfile
railway.json
requirements.txt
```

## Endpoints

### `GET /api/hello`

Prueba rápida de salud de la API.

Respuesta esperada:

```json
{
  "message": "Hola desde la API"
}
```

### `POST /api/chat`

Prueba directa del modelo/servicio IA.

Ejemplo:

```json
{
  "query": "Hola, prueba de conexión"
}
```

También puede soportar `message` o `prompt` si el schema local lo permite.

### `POST /api/chatwoot-webhook`

Endpoint principal para Chatwoot. Recibe eventos `message_created`, filtra mensajes entrantes, consulta la IA y responde en la misma conversación de Chatwoot.

URL usada en Railway:

```text
https://eia-bot-production.up.railway.app/api/chatwoot-webhook
```

### `POST /api/webhook`

Endpoint para pruebas con webhook directo de Messenger/Meta. Para el flujo real con Chatwoot se recomienda usar `/api/chatwoot-webhook`.

## Variables de entorno

Configurar en Railway dentro del servicio `eia-bot`.

### Chatwoot

```env
CHATWOOT_BASE_URL=https://chat.ecommer.shop
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_API_ACCESS_TOKEN=...
```

`CHATWOOT_API_ACCESS_TOKEN` debe ser un token válido de un usuario/agente con acceso a la cuenta y a las bandejas de entrada correspondientes.

### IA / RAG

Según el servicio usado:

```env
SIMETRIA_API_URL=...
SIMETRIA_API_KEY=...
RAG_BASE_URL=...
AZURE_AI_ENDPOINT=...
AZURE_AI_KEY=...
AZURE_AI_DEPLOYMENT=...
```

No todas son obligatorias al mismo tiempo; dependen de cómo esté implementado `app/services/ai_service.py`.

### Memoria temporal con Valkey/Redis

```env
VALKEY_URL=redis://...
```

o alternativamente:

```env
REDIS_URL=redis://...
```

Si no se configura `VALKEY_URL` ni `REDIS_URL`, la API sigue funcionando, pero sin memoria temporal.

### Filtro opcional por inbox

```env
CHATWOOT_ALLOWED_INBOX_IDS=2,4
```

Usar solo si se quiere limitar el bot a ciertas bandejas. Si se deja vacío o no existe, el bot procesa cualquier inbox que llegue por el webhook.

Ejemplo:

```text
2 = WhatsApp
4 = Messenger
```

Los IDs se obtienen desde la URL de configuración de cada inbox en Chatwoot:

```text
/app/accounts/1/settings/inboxes/ID
```

## Configuración en Chatwoot

1. Ir a `Ajustes → Integraciones → Webhooks`.
2. Crear un webhook con esta URL:

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

`Dockerfile` ejecuta la API con Uvicorn:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Railway asigna automáticamente el puerto mediante la variable `PORT`.

## Probar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Luego abrir:

```text
http://127.0.0.1:8000/docs
```

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

Debe aparecer:

```text
POST /api/chatwoot-webhook 200
```

3. Si aparece `500`, revisar:

```text
eia-bot → Deployments → Deploy Logs
```

Buscar:

```text
=== ERROR CHATWOOT WEBHOOK ===
```

## Memoria de conversación

El bot puede usar Valkey/Redis para guardar una memoria temporal por `conversation_id`.

Ejemplo de clave:

```text
eia-bot:chatwoot:conversation:6:messages
```

La memoria temporal sirve para enviar a la IA los últimos mensajes de la conversación. No reemplaza el historial real de Chatwoot, que se guarda en la base de datos de Chatwoot/Postgres.

## Notas importantes

* Chatwoot guarda el historial real de conversaciones.
* Valkey/Redis se usa solo como memoria temporal o caché de contexto.
* El webhook debe escuchar `message_created`.
* Los mensajes salientes del bot deben ser ignorados por el parser para evitar bucles.
* Si Messenger no responde, revisar el `inbox_id` y la variable `CHATWOOT_ALLOWED_INBOX_IDS`.
* Si falla el envío a Chatwoot, revisar `CHATWOOT_API_ACCESS_TOKEN`, `CHATWOOT_ACCOUNT_ID` y `CHATWOOT_BASE_URL`.
