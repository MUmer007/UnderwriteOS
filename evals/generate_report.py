import json
import os
from datetime import datetime


def generate_report():
    report_path = "evals/reports/latest_run.json"
    if not os.path.exists(report_path):
        print("? No evaluation data found. Run `uv run python evals/run.py` first.")
        return

    with open(report_path) as f:
        results = json.load(f)

    valid_results = [r for r in results if "error" not in r]
    if not valid_results:
        print("? No valid results in the report.")
        return

    # 1. Aggregate Metrics
    total_docs = len(valid_results)
    avg_f1 = sum(r["txn_f1"] for r in valid_results) / total_docs

    latencies = sorted([r["latency"] for r in valid_results])
    p50_latency = latencies[len(latencies) // 2]
    p90_latency = latencies[int(len(latencies) * 0.9)]

    total_prompt_tokens = sum(r.get("prompt_tokens", 0) for r in valid_results)
    total_comp_tokens = sum(r.get("completion_tokens", 0) for r in valid_results)

    # 2. Tamper Detection
    tampered = [r for r in valid_results if r.get("is_tampered_truth")]
    tampered_caught = sum(1 for r in tampered if not r.get("reconciled", True))
    tamper_rate = tampered_caught / len(tampered) if tampered else 0

    # 3. Wrong Type Rejection
    wrong_type = [r for r in valid_results if r.get("doc_type_truth") == "invoice"]
    wrong_type_rejected = sum(
        1 for r in wrong_type if r.get("doc_type_extracted") != "bank_statement"
    )
    wrong_type_rate = wrong_type_rejected / len(wrong_type) if wrong_type else 0

    # 4. Path Accuracy
    text_path = [r for r in valid_results if r.get("path") == "text"]
    vision_path = [r for r in valid_results if r.get("path") == "vision"]

    text_f1 = sum(r["txn_f1"] for r in text_path) / len(text_path) if text_path else 0
    vision_f1 = sum(r["txn_f1"] for r in vision_path) / len(vision_path) if vision_path else 0

    # 5. Balance Exact Match
    opening_matches = sum(1 for r in valid_results if r.get("opening_match"))
    closing_matches = sum(1 for r in valid_results if r.get("closing_match"))

    # Generate Markdown
    md = f"""# UnderwriteOS Evaluation Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Dataset:** 90 synthetic documents (60 clean, 15 tampered, 15 wrong-type)

## ?? Executive Summary
| Metric | Result |
|--------|--------|
| **Total Documents Processed** | {total_docs} |
| **Average Transaction F1** | {avg_f1:.2%} |
| **Tamper Detection Rate** | {tamper_rate:.2%} ({tampered_caught}/{len(tampered)}) |
| **Wrong-Type Rejection Rate** | {wrong_type_rate:.2%} ({wrong_type_rejected}/{len(wrong_type)}) |
| **Median Latency (p50)** | {p50_latency:.2f}s |
| **90th Percentile Latency (p90)** | {p90_latency:.2f}s |
| **Total Tokens (Prompt/Comp)** | {total_prompt_tokens} / {total_comp_tokens} |

## ?? Extraction Performance by Path
| Path | Count | Avg F1 Score |
|------|-------|--------------|
| **Text (pdfplumber)** | {len(text_path)} | {text_f1:.2%} |
| **Vision (PyMuPDF raster)** | {len(vision_path)} | {vision_f1:.2%} |

## ?? Reconciliation & Guardrails
- **Opening Balance Exact Match:** {opening_matches}/{total_docs} ({opening_matches / total_docs:.2%})
- **Closing Balance Exact Match:** {closing_matches}/{total_docs} ({closing_matches / total_docs:.2%})
- **Guardrail Status:** Active. All memos are validated against deterministic metrics. Hallucinated numbers and banned phrases (e.g., "approved", "interest rate") are blocked and flagged for review.

## ?? Error Analysis (Top Failure Modes)
1. **Vision Model Date Parsing:** Occasionally misreads `MM/DD/YY` formats as `YYYY-MM-DD` or vice versa, causing transaction date mismatches (lowering F1).
2. **Running Balance Omission:** On heavily degraded (noisy) PDFs, the vision model sometimes skips the running balance column, making reconciliation fall back to opening/closing only.
3. **Description Truncation:** Long transaction descriptions are sometimes truncated by the vision model, though amount/date extraction remains robust.

## ??? Limitations
- **Synthetic Data:** Results are based on synthetically generated statements. Real-world bank statements may have more complex layouts.
- **Simplified DSCR:** The risk engine uses a simplified CFADS calculation for harness validation.
- **Not a Compliant Decisioning System:** This is an extraction and reconciliation harness, not a final credit decisioning engine.
- **Rate Limits:** Free-tier API limits were encountered; production should use dedicated endpoints or local inference.

---
*UnderwriteOS Core Principle: LLMs only extract and narrate; all risk math is deterministic, audited, and tested.*
"""

    output_path = "evals/reports/final_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print("? Evaluation report generated successfully!")
    print(f"?? View it at: {output_path}")


if __name__ == "__main__":
    generate_report()
