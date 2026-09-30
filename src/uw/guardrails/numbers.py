import re
from decimal import Decimal

# Matches numbers like 100, 1,000.50, $1,000.50, 50%
NUM_REGEX = re.compile(r"\$?\d[\d,]*\.?\d*%?")

BANNED_PHRASES = [
    r"\bapproved\b",
    r"\bapproval\b",
    r"\binterest rate\b",
    r"\bguarantee\b",
    r"\bguaranteed\b",
]


def check_memo(
    memo: str, allowed_numbers: set[Decimal], tol: Decimal = Decimal("0.005")
) -> list[str]:
    """
    Checks a generated memo for hallucinated numbers or banned phrases.
    Returns a list of violations. Empty list means the memo passed.
    """
    violations = []
    memo_lower = memo.lower()

    # 1. Check banned phrases
    for phrase in BANNED_PHRASES:
        if re.search(phrase, memo_lower):
            violations.append(f"Banned phrase detected: '{phrase.strip(r'\b')}'")

    # 2. Check numbers
    for match in NUM_REGEX.finditer(memo):
        tok = match.group()
        try:
            clean_tok = tok.strip("$%").replace(",", "")
            v = Decimal(clean_tok)
        except Exception:
            continue

        # Check if this number is close to any allowed number
        is_allowed = False
        for allowed in allowed_numbers:
            # Tolerance check: within 0.5% of the allowed number
            tolerance = tol * max(abs(allowed), Decimal("1"))
            if abs(v - allowed) <= tolerance:
                is_allowed = True
                break

        if not is_allowed:
            violations.append(f"Unsupported/hallucinated number found: '{tok}'")

    return violations
