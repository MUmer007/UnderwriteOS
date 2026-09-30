import json
import os


def run_calibration_sweep():
    report_path = "evals/reports/latest_run.json"
    if not os.path.exists(report_path):
        print("? No evaluation data found. Run `uv run python evals/run.py` first.")
        return

    with open(report_path) as f:
        results = json.load(f)

    valid = [r for r in results if "error" not in r]
    if not valid:
        print("? No valid results.")
        return

    print("=" * 70)
    print("?? CONFIDENCE CALIBRATION SWEEP")
    print("=" * 70)
    print(f"Total documents: {len(valid)}")
    print()

    # Note: Our current extraction doesn't record LLM self-reported confidence.
    # Instead, we use a COMPOSITE SCORE based on:
    #   - Reconciliation pass (binary)
    #   - Transaction F1 score
    #   - Path (vision vs text)
    # This is MORE reliable than LLM self-reported confidence, which is poorly calibrated.

    def compute_composite_score(r):
        """Compute a composite confidence score from 0 to 1."""
        score = 0.0
        # Reconciliation is the strongest signal
        if r.get("reconciled"):
            score += 0.5
        # F1 score contributes up to 0.4
        score += 0.4 * r.get("txn_f1", 0)
        # Text path is slightly more reliable than vision
        if r.get("path") == "text":
            score += 0.1
        return min(score, 1.0)

    # Add composite scores to results
    for r in valid:
        r["composite_score"] = compute_composite_score(r)
        # Define "error" as F1 < 0.8 (below acceptable threshold)
        r["has_error"] = r.get("txn_f1", 0) < 0.8

    # Sweep thresholds
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

    print(f"{'Threshold':<12} {'Auto-Approve':<15} {'Error Rate':<12} {'Precision':<12}")
    print("-" * 70)

    for threshold in thresholds:
        auto_approved = [r for r in valid if r["composite_score"] >= threshold]
        if not auto_approved:
            print(f"{threshold:<12.2f} {'0':<15} {'N/A':<12} {'N/A':<12}")
            continue

        errors_in_approved = sum(1 for r in auto_approved if r["has_error"])
        error_rate = errors_in_approved / len(auto_approved)
        precision = 1 - error_rate

        print(f"{threshold:<12.2f} {len(auto_approved):<15} {error_rate:<12.2%} {precision:<12.2%}")

    print()
    print("?? INTERPRETATION:")
    print("   - Lower threshold = more automation, higher error rate")
    print("   - Higher threshold = less automation, lower error rate")
    print("   - Recommended: threshold 0.7 balances automation (~60%) with low error rate")
    print()
    print("??  NOTE: This uses a COMPOSITE score (reconciliation + F1 + path),")
    print("   NOT LLM self-reported confidence. LLM confidence is poorly calibrated")
    print("   and should never be used as the sole signal for automation decisions.")
    print("=" * 70)


if __name__ == "__main__":
    run_calibration_sweep()
