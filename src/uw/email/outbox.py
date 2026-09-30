import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import text
from sqlalchemy.orm import Session

from uw.models import EmailOutbox


def generate_idempotency_key(deal_id: str, template: str, doc_type: str, attempt: int) -> str:
    payload = f"{deal_id}:{template}:{doc_type}:{attempt}"
    return hashlib.sha256(payload.encode()).hexdigest()


def send_idempotent_email(
    session: Session,
    deal_id: str,
    to_email: str,
    subject: str,
    body: str,
    template_name: str,
    doc_type: str,
    attempt: int = 1,
    smtp_host: str = "localhost",
    smtp_port: int = 1025,
) -> bool:
    key = generate_idempotency_key(deal_id, template_name, doc_type, attempt)
    message_id = f"<{key}@underwriteos>"

    # 1. Try to insert with ON CONFLICT DO NOTHING (atomic)
    insert_stmt = text("""
        INSERT INTO email_outbox (key, deal_id, status, message_id)
        VALUES (:key, :deal_id, 'sending', :message_id)
        ON CONFLICT (key) DO NOTHING
    """)
    result = session.execute(
        insert_stmt, {"key": key, "deal_id": deal_id, "message_id": message_id}
    )

    if result.rowcount == 0:
        existing = session.get(EmailOutbox, key)
        if existing and existing.status == "sent":
            return True  # Effectively-once: already sent

    # 2. Send the email
    msg = MIMEMultipart()
    msg["From"] = "underwriteos@localhost"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Message-ID"] = message_id
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)

        # 3. Mark as sent
        session.execute(
            text("UPDATE email_outbox SET status = 'sent' WHERE key = :key"), {"key": key}
        )
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Failed to send email: {e}")
        return False
