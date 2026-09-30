import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DealStage(enum.Enum):
    discovery = "discovery"
    doc_collection = "doc_collection"
    underwriting = "underwriting"
    committee = "committee"
    funded = "funded"


class JobStatus(enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    stage: Mapped[DealStage] = mapped_column(Enum(DealStage), default=DealStage.discovery)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[str] = mapped_column(String, ForeignKey("deals.id"))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    key: Mapped[str] = mapped_column(String, primary_key=True)  # sha256 hash
    deal_id: Mapped[str] = mapped_column(String, ForeignKey("deals.id"))
    status: Mapped[str] = mapped_column(String, default="sending")
    message_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditTrail(Base):
    __tablename__ = "ai_audit_trail"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
