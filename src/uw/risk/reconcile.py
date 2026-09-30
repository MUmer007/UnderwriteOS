from decimal import Decimal
from typing import List, Tuple

def reconcile(
    opening: Decimal, 
    closing: Decimal, 
    amounts: List[Decimal],
    tol: Decimal = Decimal("0.01")
) -> Tuple[bool, Decimal]:
    """
    Checks if opening_balance + sum(transactions) == closing_balance.
    Returns (is_valid, difference).
    """
    calculated_closing = opening + sum(amounts, Decimal("0"))
    diff = calculated_closing - closing
    
    is_valid = abs(diff) <= tol
    return is_valid, diff