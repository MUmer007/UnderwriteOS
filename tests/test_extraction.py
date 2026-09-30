import os
from decimal import Decimal
from uw.extraction.pipeline import extract_from_pdf
from uw.risk.reconcile import reconcile

def test_single_extraction():
    # Pick a known tampered file (e.g., statement_061.pdf which had noise + tampering)
    pdf_path = "data/synthetic/tampered/statement_061.pdf"
    truth_path = "data/synthetic/truth/statement_061.json"
    
    if not os.path.exists(pdf_path):
        print("⚠️ Test file not found. Run Phase 1 first.")
        return

    print(f"\n🔍 Testing extraction on: {pdf_path}")
    
        # 1. Extract
    text_model = os.environ.get("TEXT_MODEL", "qwen/qwen3.8-27b:free")
    vision_model = os.environ.get("VISION_MODEL", "qwen/qwen3.8-27b:free")
   
    
    extraction = extract_from_pdf(pdf_path, text_model, vision_model)
    result = extraction["result"]
    
    print(f"✅ Extracted via: {extraction['path']}")
    print(f"   Bank: {result.bank_name}")
    print(f"   Transactions found: {len(result.transactions)}")
    print(f"   Extracted Opening: {result.opening_balance}")
    print(f"   Extracted Closing: {result.closing_balance}")

    # 2. Reconcile
    if result.opening_balance is not None and result.closing_balance is not None:
        amounts = [t.amount for t in result.transactions]
        is_valid, diff = reconcile(result.opening_balance, result.closing_balance, amounts)
        
        print(f"\n⚖️  Reconciliation Check:")
        print(f"   Valid: {is_valid}")
        print(f"   Difference: ${diff}")
        
        if not is_valid:
            print("   🚨 TAMPER DETECTED or EXTRACTION ERROR! (This is expected for this file)")

if __name__ == "__main__":
    test_single_extraction()