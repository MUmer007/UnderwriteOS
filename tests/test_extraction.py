import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "",
    reason="OPENAI_API_KEY not set - skipping LLM-dependent tests",
)

from uw.extraction.pipeline import extract_from_pdf  # noqa: E402
from uw.risk.reconcile import reconcile  # noqa: E402


def test_single_extraction():
    pdf_path = "data/synthetic/tampered/statement_061.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip("Test file not found. Run Phase 1 first.")

    print(f"\n?? Testing extraction on: {pdf_path}")

    text_model = os.environ.get("TEXT_MODEL", "qwen/qwen3.7-flash")
    vision_model = os.environ.get("VISION_MODEL", "qwen/qwen3.7-flash")

    extraction = extract_from_pdf(pdf_path, text_model, vision_model)
    result = extraction["result"]

    print(f"? Extracted via: {extraction['path']}")
    print(f"   Bank: {result.bank_name}")
    print(f"   Transactions found: {len(result.transactions)}")
    print(f"   Extracted Opening: {result.opening_balance}")
    print(f"   Extracted Closing: {result.closing_balance}")

    if result.opening_balance is not None and result.closing_balance is not None:
        amounts = [t.amount for t in result.transactions]
        is_valid, diff = reconcile(result.opening_balance, result.closing_balance, amounts)

        print("\n??  Reconciliation Check:")
        print(f"   Valid: {is_valid}")
        print(f"   Difference: ${diff}")
