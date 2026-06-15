"""
Capa de base de datos con asyncpg.

Usa el schema 'ecommer_bot' para no chocar con las tablas de Chatwoot
que viven en el schema 'public' del mismo Postgres de Railway.
"""
import json
from typing import Optional, List, Dict
import asyncpg
from app.config import get_settings

settings = get_settings()
_pool: Optional[asyncpg.Pool] = None

SCHEMA = "ecommer_bot"


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.stores (
                id              SERIAL PRIMARY KEY,
                name            TEXT NOT NULL,
                inbox_id        INTEGER UNIQUE,
                system_prompt   TEXT,
                plan            TEXT DEFAULT 'standard',
                created_at      TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS {SCHEMA}.conversations (
                id              SERIAL PRIMARY KEY,
                conversation_id INTEGER UNIQUE NOT NULL,
                account_id      INTEGER NOT NULL,
                customer_phone  TEXT,
                handoff_active  BOOLEAN DEFAULT FALSE,
                history         JSONB DEFAULT '[]'::jsonb,
                last_message    TIMESTAMP DEFAULT NOW(),
                created_at      TIMESTAMP DEFAULT NOW()
            );
            """
        )


async def close_db() -> None:
    if _pool:
        await _pool.close()


async def get_handoff(conversation_id: int) -> bool:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT handoff_active FROM {SCHEMA}.conversations WHERE conversation_id = $1",
            conversation_id,
        )
        return bool(row["handoff_active"]) if row else False


async def set_handoff(conversation_id: int, active: bool) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {SCHEMA}.conversations (conversation_id, account_id, handoff_active)
            VALUES ($1, 1, $2)
            ON CONFLICT (conversation_id)
            DO UPDATE SET handoff_active = $2, last_message = NOW()
            """,
            conversation_id, active,
        )


async def get_history(conversation_id: int) -> List[Dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT history FROM {SCHEMA}.conversations WHERE conversation_id = $1",
            conversation_id,
        )
        if row and row["history"]:
            return json.loads(row["history"]) if isinstance(row["history"], str) else row["history"]
        return []


async def append_history(
    conversation_id: int, account_id: int, role: str, content: str,
    max_turns: int = 10,
) -> None:
    history = await get_history(conversation_id)
    history.append({"role": role, "content": content})
    history = history[-(max_turns * 2):]

    async with _pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {SCHEMA}.conversations (conversation_id, account_id, history, last_message)
            VALUES ($1, $2, $3::jsonb, NOW())
            ON CONFLICT (conversation_id)
            DO UPDATE SET history = $3::jsonb, last_message = NOW()
            """,
            conversation_id, account_id, json.dumps(history),
        )


async def get_system_prompt(inbox_id) -> str:
    if inbox_id is None:
        return settings.DEFAULT_SYSTEM_PROMPT
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT system_prompt FROM {SCHEMA}.stores WHERE inbox_id = $1", inbox_id,
        )
        if row and row["system_prompt"]:
            return row["system_prompt"]
    return settings.DEFAULT_SYSTEM_PROMPT