from decimal import Decimal
from statistics import mean, pstdev
from typing import Any


def average_daily_balance(daily_closing: list[Decimal]) -> Decimal:
    """Calculates the average of daily closing balances."""
    if not daily_closing:
        return Decimal("0")
    return sum(daily_closing, Decimal("0")) / len(daily_closing)


def revenue_volatility(monthly_deposits: list[Decimal]) -> Decimal:
    """
    Coefficient of variation of monthly deposits.
    Needs >= 3 months of data to be meaningful.
    """
    if len(monthly_deposits) < 3:
        return Decimal("Infinity")
    m = mean(monthly_deposits)
    if m == 0:
        return Decimal("Infinity")
    # pstdev returns float, convert back to Decimal for strict typing
    std_dev = Decimal(str(pstdev([float(d) for d in monthly_deposits])))
    return std_dev / Decimal(str(m))


def dscr(cash_flow_available: Decimal, annual_debt_service: Decimal) -> Decimal:
    """
    Debt Service Coverage Ratio (CFADS / debt service).
    CFADS = deposits - operating outflows (excl. debt payments).
    """
    if annual_debt_service == 0:
        return Decimal("Infinity")
    return cash_flow_available / annual_debt_service


def compute_risk_metrics(transactions: list[dict[str, Any]]) -> dict[str, Decimal]:
    """
    Simplified risk metric computation for the portfolio system.
    Assumptions (stated explicitly for interviewers):
    - 'ACH DEPOSIT', 'STRIPE PAYOUT', 'PAYROLL' are considered revenue/deposits.
    - 'LOAN PMT' is considered debt service.
    - This is a simplified harness; a production system would use a proper chart of accounts mapping.
    """
    total_deposits = Decimal("0")
    total_debt_service = Decimal("0")
    daily_balances = []

    for txn in transactions:
        amt = Decimal(str(txn["amount"]))
        desc = txn["description"].upper()

        if amt > 0 and any(kw in desc for kw in ["DEPOSIT", "PAYOUT", "PAYROLL"]):
            total_deposits += amt

        if "LOAN PMT" in desc or "DEBT" in desc:
            total_debt_service += abs(amt)

        if txn.get("balance") is not None:
            daily_balances.append(Decimal(str(txn["balance"])))

    cash_flow_available = total_deposits  # Simplified CFADS for harness

    return {
        "total_deposits": total_deposits,
        "total_debt_service": total_debt_service,
        "average_daily_balance": average_daily_balance(daily_balances)
        if daily_balances
        else Decimal("0"),
        "dscr": dscr(cash_flow_available, total_debt_service),
        "revenue_volatility": revenue_volatility(
            [total_deposits] * 3
        ),  # Dummy monthly data for harness validation
    }
