from decimal import Decimal
from uw.risk.engine import compute_risk_metrics
from uw.guardrails.numbers import check_memo

def test_guardrail_blocks_hallucinations():
    # 1. Setup: Fake extracted transactions
    fake_txns = [
        {"description": "ACH DEPOSIT", "amount": "5000.00", "balance": "15000.00"},
        {"description": "RENT", "amount": "-2000.00", "balance": "13000.00"},
        {"description": "LOAN PMT", "amount": "-500.00", "balance": "12500.00"}
    ]
    
    # 2. Compute deterministic metrics
    metrics = compute_risk_metrics(fake_txns)
    
    # Build the "allowed" set of numbers (the metrics + some rounded variants)
    allowed_numbers = set(metrics.values())
    allowed_numbers.add(Decimal("5000")) # Exact match variant
    
    # 3. Test a BAD memo (contains hallucinated number and banned phrase)
    bad_memo = (
        "The applicant has total deposits of $5,000.00. "
        "Their DSCR is 10.0. We guarantee approval at a 5% interest rate."
    )
    
    bad_violations = check_memo(bad_memo, allowed_numbers)
    assert len(bad_violations) > 0, "Guardrail should have caught violations"
    assert any("interest rate" in v.lower() for v in bad_violations), "Should catch banned phrase"
    assert any("10.0" in v or "5" in v for v in bad_violations), "Should catch hallucinated numbers"
    print("✅ Guardrail successfully BLOCKED the bad memo.")
    
    # 4. Test a GOOD memo (only uses allowed numbers, no banned phrases)
    good_memo = (
        f"The applicant has total deposits of ${metrics['total_deposits']}. "
        f"Their average daily balance is ${metrics['average_daily_balance']}. "
        f"Further manual review is required."
    )
    
    good_violations = check_memo(good_memo, allowed_numbers)
    assert len(good_violations) == 0, f"Guardrail should have passed the good memo, but found: {good_violations}"
    print("✅ Guardrail successfully PASSED the clean memo.")

if __name__ == "__main__":
    test_guardrail_blocks_hallucinations()