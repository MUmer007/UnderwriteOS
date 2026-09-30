import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from uw.models import Base

# Setup DB
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://uw:uw@localhost:5433/uw")
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

app = FastAPI(title="UnderwriteOS")

# Setup explicit Jinja2 Environment
template_dir = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"])
)


def render_template(name: str, **context):
    template = jinja_env.get_template(name)
    return HTMLResponse(content=template.render(**context))


@app.get("/", response_class=HTMLResponse)
async def root():
    return render_template("deals.html")


@app.get("/deals", response_class=HTMLResponse)
async def list_deals():
    with Session(engine) as session:
        result = session.execute(
            text("SELECT id, stage, created_at FROM deals ORDER BY created_at DESC")
        )
        deals = [dict(row._mapping) for row in result.fetchall()]
    return render_template("deals.html", deals=deals)


@app.get("/deals/{deal_id}", response_class=HTMLResponse)
async def deal_detail(deal_id: str):
    mock_state = {
        "deal_id": deal_id,
        "extraction_path": "vision",
        "reconciled": False,
        "reconcile_diff": "12.50",
        "metrics": {
            "total_deposits": "45,250.00",
            "average_daily_balance": "18,430.50",
            "dscr": "1.42",
        },
        "memo": "Applicant shows total deposits of $45,250.00 over the statement period. Average daily balance is $18,430.50, indicating stable cash reserves. Calculated DSCR is 1.42x, which is below the 1.50x portfolio minimum threshold. Reconciliation status: Failed (Variance: $12.50). Manual review of line-item transactions is required to identify the discrepancy.",
        "guardrail_violations": [
            "Unsupported/hallucinated number found: '1.50' (Threshold minimum mentioned, but not in extracted metrics)"
        ],
        "needs_review": True,
    }
    return render_template("deal_detail.html", state=mock_state)


@app.post("/deals/{deal_id}/approve")
async def approve_deal(deal_id: str):
    with Session(engine) as session:
        session.execute(
            text("UPDATE deals SET stage = 'committee' WHERE id = :id"), {"id": deal_id}
        )
        session.commit()
    return HTMLResponse("""
        <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex items-center gap-3">
            <svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>
                <h4 class="text-sm font-semibold text-emerald-900">Deal Approved</h4>
                <p class="text-sm text-emerald-700">This deal has been successfully routed to the credit committee.</p>
            </div>
        </div>
    """)


@app.post("/deals/{deal_id}/reject")
async def reject_deal(deal_id: str):
    with Session(engine) as session:
        session.execute(
            text("UPDATE deals SET stage = 'discovery' WHERE id = :id"), {"id": deal_id}
        )
        session.commit()
    return HTMLResponse("""
        <div class="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center gap-3">
            <svg class="w-6 h-6 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>
                <h4 class="text-sm font-semibold text-rose-900">Deal Rejected</h4>
                <p class="text-sm text-rose-700">This deal has been returned to discovery. An email notification has been queued.</p>
            </div>
        </div>
    """)
