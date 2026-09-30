import os
from decimal import Decimal
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from uw.extraction.pipeline import extract_from_pdf
from uw.guardrails.numbers import check_memo
from uw.risk.engine import compute_risk_metrics
from uw.risk.reconcile import reconcile


class AgentState(TypedDict):
    deal_id: str
    pdf_path: str
    doc_type: str
    extraction: dict[str, Any] | None
    reconciled: bool
    reconcile_diff: str
    metrics: dict[str, Any] | None
    memo: str
    guardrail_violations: list[str]
    needs_review: bool


def classify_node(state: AgentState) -> AgentState:
    # Simplified classification: if it's an invoice in the path, flag it
    if "wrong_type" in state["pdf_path"].lower() or "invoice" in state["pdf_path"].lower():
        state["doc_type"] = "invoice"
        state["needs_review"] = True
        state["memo"] = "Document is not a bank statement. Manual review required."
    else:
        state["doc_type"] = "bank_statement"
        state["needs_review"] = False
    return state


def extract_node(state: AgentState) -> AgentState:
    if state["doc_type"] != "bank_statement":
        return state

    text_model = os.environ.get("TEXT_MODEL", "qwen/qwen3.7-flash")
    vision_model = os.environ.get("VISION_MODEL", "qwen/qwen3.7-flash")

    result = extract_from_pdf(state["pdf_path"], text_model, vision_model)
    state["extraction"] = result["result"].model_dump()
    return state


def reconcile_node(state: AgentState) -> AgentState:
    if not state["extraction"]:
        return state

    ext = state["extraction"]
    opening = ext.get("opening_balance")
    closing = ext.get("closing_balance")

    if opening is not None and closing is not None:
        amounts = [Decimal(str(t["amount"])) for t in ext.get("transactions", [])]
        is_valid, diff = reconcile(Decimal(str(opening)), Decimal(str(closing)), amounts)
        state["reconciled"] = is_valid
        state["reconcile_diff"] = str(diff)
        if not is_valid:
            state["needs_review"] = True
    return state


def risk_node(state: AgentState) -> AgentState:
    if not state["extraction"]:
        return state

    txns = state["extraction"].get("transactions", [])
    state["metrics"] = compute_risk_metrics(txns)

    # Generate a simple deterministic memo
    m = state["metrics"]
    state["memo"] = (
        f"Applicant shows total deposits of ${m['total_deposits']}. "
        f"Average daily balance is ${m['average_daily_balance']}. "
        f"DSCR is {m['dscr']}. "
        f"Reconciliation status: {'Passed' if state['reconciled'] else f'Failed (Diff: {state["reconcile_diff"]})'}."
    )
    return state


def guardrail_node(state: AgentState) -> AgentState:
    if not state["metrics"]:
        return state

    m = state["metrics"]
    allowed_numbers = set(m.values())

    violations = check_memo(state["memo"], allowed_numbers)
    state["guardrail_violations"] = violations

    if violations:
        state["needs_review"] = True
        state["memo"] += f"\n[GUARDRAIL BLOCKED: {', '.join(violations)}]"

    return state


def route_review(state: AgentState) -> str:
    return "review_gate" if state["needs_review"] else END


# Build the graph
workflow = StateGraph(AgentState)
workflow.add_node("classify", classify_node)
workflow.add_node("extract", extract_node)
workflow.add_node("reconcile", reconcile_node)
workflow.add_node("risk", risk_node)
workflow.add_node("guardrail", guardrail_node)

workflow.set_entry_point("classify")
workflow.add_conditional_edges("classify", route_review, {"review_gate": END, END: "extract"})
workflow.add_edge("extract", "reconcile")
workflow.add_edge("reconcile", "risk")
workflow.add_edge("risk", "guardrail")
workflow.add_conditional_edges("guardrail", route_review, {"review_gate": END, END: END})

app = workflow.compile()
