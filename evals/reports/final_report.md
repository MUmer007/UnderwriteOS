# UnderwriteOS Evaluation Report
**Generated:** 2026-09-29 11:57:21
**Dataset:** 90 synthetic documents (60 clean, 15 tampered, 15 wrong-type)

## ?? Executive Summary
| Metric | Result |
|--------|--------|
| **Total Documents Processed** | 90 |
| **Average Transaction F1** | 53.79% |
| **Tamper Detection Rate** | 100.00% (15/15) |
| **Wrong-Type Rejection Rate** | 100.00% (15/15) |
| **Median Latency (p50)** | 57.25s |
| **90th Percentile Latency (p90)** | 85.34s |
| **Total Tokens (Prompt/Comp)** | 397477 / 471263 |

## ?? Extraction Performance by Path
| Path | Count | Avg F1 Score |
|------|-------|--------------|
| **Text (pdfplumber)** | 35 | 68.63% |
| **Vision (PyMuPDF raster)** | 55 | 44.35% |

## ?? Reconciliation & Guardrails
- **Opening Balance Exact Match:** 55/90 (61.11%)
- **Closing Balance Exact Match:** 63/90 (70.00%)
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
