import os
import json
import time
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env file before anything else
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Local import since we are already inside the evals directory
from metrics import calculate_transaction_metrics, calculate_balance_metrics
from uw.extraction.pipeline import extract_from_pdf
from uw.risk.reconcile import reconcile

def run_evals():
    data_dir = Path("data/synthetic")
    truth_dir = Path("data/synthetic/truth")
    
    text_model = os.environ.get("TEXT_MODEL", "google/gemma-4-26b-a4b-it:free")
    vision_model = os.environ.get("VISION_MODEL", "google/gemma-4-26b-a4b-it:free")
    results = []
    
    # Collect all PDFs
    pdf_files = []
    for category in ["clean", "tampered", "wrong_type"]:
        folder = data_dir / category
        if folder.exists():
            pdf_files.extend(folder.glob("*.pdf"))
            
    print(f"?? Starting evaluation on {len(pdf_files)} documents...")
    
    total_latency = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    for pdf_path in pdf_files:
        filename = pdf_path.stem
        truth_path = truth_dir / f"{filename}.json"
        
        if not truth_path.exists():
            print(f"??  Skipping {filename}: No truth file found.")
            continue
            
        print(f"\n?? Processing: {filename} ({pdf_path.parent.name})")
        
        # 1. Load truth
        with open(truth_path, "r") as f:
            truth = json.load(f)
            
        # 2. Extract
        try:
            extraction = extract_from_pdf(str(pdf_path), text_model, vision_model)
            total_latency += extraction["latency"]
            total_prompt_tokens += extraction["usage"].get("prompt_tokens", 0)
            total_completion_tokens += extraction["usage"].get("completion_tokens", 0)
            
            result = extraction["result"]
            
            # 3. Reconcile
            is_reconciled = False
            diff = Decimal("0")
            if result.opening_balance is not None and result.closing_balance is not None:
                amounts = [t.amount for t in result.transactions]
                is_reconciled, diff = reconcile(result.opening_balance, result.closing_balance, amounts)
                
            # 4. Metrics
            txn_metrics = calculate_transaction_metrics(
                truth.get("txns", []), 
                [t.model_dump() for t in result.transactions]
            )
            balance_metrics = calculate_balance_metrics(truth, result.model_dump())
            
            # 5. Record result
            results.append({
                "filename": filename,
                "category": pdf_path.parent.name,
                "is_tampered_truth": truth.get("is_tampered", False),
                "doc_type_truth": truth.get("doc_type", "unknown"),
                "doc_type_extracted": "bank_statement" if result.is_bank_statement else "other",
                "path": extraction["path"],
                "latency": extraction["latency"],
                "prompt_tokens": extraction["usage"].get("prompt_tokens", 0),
                "completion_tokens": extraction["usage"].get("completion_tokens", 0),
                "txn_f1": txn_metrics["f1"],
                "opening_match": balance_metrics["opening_exact_match"],
                "closing_match": balance_metrics["closing_exact_match"],
                "reconciled": is_reconciled,
                "reconcile_diff": str(diff)
            })
            
            print(f"   ? F1: {txn_metrics['f1']:.2f} | Reconciled: {is_reconciled} | Path: {extraction['path']}")
            
        except Exception as e:
            print(f"   ? Failed: {e}")
            results.append({
                "filename": filename,
                "category": pdf_path.parent.name,
                "error": str(e)
            })

    # Aggregate Report
    print("\n" + "="*70)
    print("?? UNDERWRITEOS EVALUATION REPORT")
    print("="*70)
    
    # Filter out errors for aggregation
    valid_results = [r for r in results if "error" not in r]
    
    if not valid_results:
        print("No valid results to aggregate.")
        return
        
    avg_f1 = sum(r["txn_f1"] for r in valid_results) / len(valid_results)
    avg_latency = total_latency / len(valid_results)
    
    # Tamper detection rate (a tampered doc is "caught" if reconciliation FAILS)
    tampered_results = [r for r in valid_results if r["is_tampered_truth"]]
    tampered_caught = sum(1 for r in tampered_results if not r["reconciled"])
    tamper_detection_rate = tampered_caught / len(tampered_results) if tampered_results else 0
    
    # Wrong type accuracy (an invoice is "correctly handled" if NOT classified as bank_statement)
    wrong_type_results = [r for r in valid_results if r["doc_type_truth"] == "invoice"]
    wrong_type_correct = sum(1 for r in wrong_type_results if r["doc_type_extracted"] != "bank_statement")
    wrong_type_accuracy = wrong_type_correct / len(wrong_type_results) if wrong_type_results else 0

    print(f"Total Documents Processed : {len(valid_results)}")
    print(f"Average Transaction F1      : {avg_f1:.2%}")
    print(f"Average Latency per Doc     : {avg_latency:.2f}s")
    print(f"Total Tokens (Prompt/Comp)  : {total_prompt_tokens} / {total_completion_tokens}")
    print(f"Tamper Detection Rate       : {tamper_detection_rate:.2%} ({tampered_caught}/{len(tampered_results)})")
    print(f"Wrong-Type Rejection Rate   : {wrong_type_accuracy:.2%} ({wrong_type_correct}/{len(wrong_type_results)})")
    print("="*70)
    
    # Save detailed report
    os.makedirs("evals/reports", exist_ok=True)
    report_path = "evals/reports/latest_run.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"?? Detailed results saved to {report_path}")

if __name__ == "__main__":
    run_evals()
