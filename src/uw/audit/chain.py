import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


def entry_hash(prev_hash: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


def append_audit_log(
    session: Session,
    actor: str,
    model: str,
    prompt: str,
    response: str,
    tokens: int,
    latency_ms: int,
    idempotency_key: str,
) -> str:
    latest = session.execute(
        text("SELECT hash FROM ai_audit_trail ORDER BY id DESC LIMIT 1")
    ).scalar_one_or_none()
    prev_hash = latest or "0" * 64

    payload = {
        "actor": actor,
        "model": model,
        "prompt": prompt,
        "response": response,
        "tokens": tokens,
        "latency_ms": latency_ms,
        "idempotency_key": idempotency_key,
    }
    new_hash = entry_hash(prev_hash, payload)

    session.execute(text("SELECT pg_advisory_xact_lock(42)"))

    latest_locked = session.execute(
        text("SELECT hash FROM ai_audit_trail ORDER BY id DESC LIMIT 1 FOR UPDATE")
    ).scalar_one_or_none()
    if latest_locked and latest_locked != prev_hash:
        prev_hash = latest_locked
        new_hash = entry_hash(prev_hash, payload)

    insert_stmt = text("""
        INSERT INTO ai_audit_trail 
        (prev_hash, hash, idempotency_key, actor, model, prompt, response, tokens, latency_ms, created_at)
        VALUES (:prev_hash, :hash, :idempotency_key, :actor, :model, :prompt, :response, :tokens, :latency_ms, :created_at)
    """)
    session.execute(
        insert_stmt,
        {
            "prev_hash": prev_hash,
            "hash": new_hash,
            "idempotency_key": idempotency_key,
            "actor": actor,
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "created_at": datetime.now(UTC),
        },
    )
    return new_hash


def verify_chain(session: Session) -> tuple[bool, str]:
    rows = session.execute(
        text(
            "SELECT id, prev_hash, hash, actor, model, prompt, response, tokens, latency_ms, idempotency_key FROM ai_audit_trail ORDER BY id ASC"
        )
    ).fetchall()
    if not rows:
        return True, "Chain is empty (valid)"

    current_hash = "0" * 64
    for row in rows:
        payload = {
            "actor": row.actor,
            "model": row.model,
            "prompt": row.prompt,
            "response": row.response,
            "tokens": row.tokens,
            "latency_ms": row.latency_ms,
            "idempotency_key": row.idempotency_key,
        }
        expected_hash = entry_hash(current_hash, payload)
        if row.prev_hash != current_hash:
            return False, f"Chain broken at ID {row.id}: prev_hash mismatch"
        if row.hash != expected_hash:
            return False, f"Chain broken at ID {row.id}: hash mismatch"
        current_hash = row.hash
    return True, "Chain is valid"
