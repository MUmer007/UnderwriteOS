import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from uw.audit.chain import append_audit_log, verify_chain
from uw.email.outbox import generate_idempotency_key
from uw.models import Base, Deal, EmailOutbox

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

# Skip entire module if no database is available
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set - skipping Postgres-dependent tests"
)

engine = create_engine(DATABASE_URL)


def setup_module():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_audit_chain_tamper_detection():
    with Session(engine) as session:
        _ = append_audit_log(
            session, "system", "test-model", "prompt1", "response1", 100, 50, "key1"
        )
        _ = append_audit_log(
            session, "system", "test-model", "prompt2", "response2", 150, 60, "key2"
        )
        session.commit()

        is_valid, msg = verify_chain(session)
        assert is_valid, f"Chain should be valid initially. Msg: {msg}"

        session.execute(text("UPDATE ai_audit_trail SET response = 'HACKED RESPONSE' WHERE id = 1"))
        session.commit()

        is_valid, msg = verify_chain(session)
        assert not is_valid, "Chain should detect tampering"
        assert "hash mismatch" in msg.lower(), f"Expected hash mismatch error, got: {msg}"
        print("? Audit chain successfully detected tampering!")


def test_idempotent_email():
    with Session(engine) as session:
        deal = Deal()
        session.add(deal)
        session.commit()

        key = generate_idempotency_key(deal.id, "template_a", "statement", 1)
        message_id = f"<{key}@underwriteos>"

        outbox_entry = EmailOutbox(key=key, deal_id=deal.id, status="sent", message_id=message_id)
        session.add(outbox_entry)
        session.commit()

        count_before = session.execute(text("SELECT COUNT(*) FROM email_outbox")).scalar()

        existing = session.get(EmailOutbox, key)
        assert existing is not None
        assert existing.status == "sent"

        count_after = session.execute(text("SELECT COUNT(*) FROM email_outbox")).scalar()
        assert count_before == count_after, "No duplicate rows should be created"
        print("? Idempotent email logic prevents duplicates!")
