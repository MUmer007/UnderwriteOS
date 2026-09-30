import contextlib
from decimal import Decimal, InvalidOperation


def normalize_date(date_str: str) -> str:
    return str(date_str).replace("/", "-")


def calculate_transaction_metrics(
    truth_txns: list[dict], extracted_txns: list[dict]
) -> dict[str, float]:
    truth_set = set()
    for t in truth_txns:
        with contextlib.suppress(InvalidOperation, KeyError, TypeError):
            truth_set.add((normalize_date(t["date"]), str(Decimal(t["amount"]))))

    extracted_set = set()
    for t in extracted_txns:
        with contextlib.suppress(InvalidOperation, KeyError, TypeError):
            extracted_set.add(
                (normalize_date(t.get("date", "")), str(Decimal(str(t.get("amount", 0)))))
            )

    true_positives = len(truth_set.intersection(extracted_set))
    false_positives = len(extracted_set - truth_set)
    false_negatives = len(truth_set - extracted_set)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
    }


def calculate_balance_metrics(truth: dict, extracted: dict) -> dict[str, bool]:
    def dec(val):
        try:
            return Decimal(str(val))
        except (InvalidOperation, TypeError, ValueError):
            return None

    t_open = dec(truth.get("opening"))
    t_close = dec(truth.get("closing"))
    e_open = dec(extracted.get("opening_balance"))
    e_close = dec(extracted.get("closing_balance"))

    return {
        "opening_exact_match": t_open == e_open if t_open and e_open else False,
        "closing_exact_match": t_close == e_close if t_close and e_close else False,
    }


if __name__ == "__main__":
    print("? Eval harness loaded. Ready to grade Phase 2 extraction.")
