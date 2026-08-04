"""
Postgres access for durable session storage (feeds incident-log and notes
long-term memory -- separate from short-term memory, which stays in the
in-memory LangGraph checkpointer).

Uses plain SYNCHRONOUS psycopg, run via asyncio.to_thread() from each
async wrapper below -- psycopg's async mode requires a selector event
loop, but uvicorn (which Gradio runs on) forces a proactor loop on
Windows, so async psycopg can't be used from inside a live Gradio
request. Sync psycopg in a thread has no such restriction.

Table creation is one-time setup, NOT run by the app itself -- run this
file directly once (`uv run python -m src.utils.pgdb`) to create the
tables, then the app just uses the functions below on every run.
"""

import os
import asyncio
import psycopg

from dotenv import load_dotenv
load_dotenv()


def connect():
    return psycopg.connect(os.getenv("POSTGRES_URL"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_memory_status (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
    incident_memory_processed BOOLEAN NOT NULL DEFAULT FALSE,
    notes_memory_processed BOOLEAN NOT NULL DEFAULT FALSE,
    incident_memory_processed_at TIMESTAMPTZ,
    notes_memory_processed_at TIMESTAMPTZ
);
"""


def create_schema_sync() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)


async def create_schema() -> None:
    await asyncio.to_thread(create_schema_sync)


def save_turn_sync(session_id: str, query: str, tool_calls: list, final_answer: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id) VALUES (%s) ON CONFLICT (session_id) DO NOTHING",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO session_memory_status (session_id) VALUES (%s) ON CONFLICT (session_id) DO NOTHING",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (session_id, query),
        )
        for call in tool_calls:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (%s, 'tool', %s)",
                (session_id, call["result"]),
            )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'assistant', %s)",
            (session_id, final_answer),
        )


async def save_turn(session_id: str, query: str, tool_calls: list, final_answer: str) -> None:
    await asyncio.to_thread(save_turn_sync, session_id, query, tool_calls, final_answer)


def get_unprocessed_sessions_sync() -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT session_id FROM session_memory_status "
            "WHERE incident_memory_processed = FALSE OR notes_memory_processed = FALSE"
        ).fetchall()
        return [r[0] for r in rows]


async def get_unprocessed_sessions() -> list[str]:
    return await asyncio.to_thread(get_unprocessed_sessions_sync)


def get_session_messages_sync(session_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = %s "
            "AND role IN ('user', 'assistant') ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [{"role": role, "content": content} for role, content in rows]


async def get_session_messages(session_id: str) -> list[dict]:
    return await asyncio.to_thread(get_session_messages_sync, session_id)


def mark_session_processed_sync(session_id: str, incident: bool, notes: bool) -> None:
    with connect() as conn:
        if incident:
            conn.execute(
                "UPDATE session_memory_status SET incident_memory_processed = TRUE, "
                "incident_memory_processed_at = now() WHERE session_id = %s",
                (session_id,),
            )
        if notes:
            conn.execute(
                "UPDATE session_memory_status SET notes_memory_processed = TRUE, "
                "notes_memory_processed_at = now() WHERE session_id = %s",
                (session_id,),
            )


async def mark_session_processed(session_id: str, incident: bool = False, notes: bool = False) -> None:
    await asyncio.to_thread(mark_session_processed_sync, session_id, incident, notes)


if __name__ == "__main__":
    asyncio.run(create_schema())
