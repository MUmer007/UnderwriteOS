from sqlalchemy import select, update
from sqlalchemy.orm import Session
from uw.models import Job, JobStatus
from datetime import datetime, timedelta

def claim_job(session: Session) -> Job | None:
    """Atomically claims a queued job using FOR UPDATE SKIP LOCKED."""
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.queued)
        .where(Job.run_at <= datetime.utcnow())
        .order_by(Job.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = session.execute(stmt).scalar_one_or_none()
    
    if job:
        job.status = JobStatus.running
        job.locked_at = datetime.utcnow()
        job.attempts += 1
        session.commit()
        session.refresh(job)
    return job

def requeue_stale_jobs(session: Session, timeout_seconds: int = 300):
    """Reaper: requeues jobs stuck in 'running' past a timeout."""
    cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    stmt = (
        update(Job)
        .where(Job.status == JobStatus.running)
        .where(Job.locked_at < cutoff)
        .values(status=JobStatus.queued, locked_at=None)
    )
    session.execute(stmt)
    session.commit()
