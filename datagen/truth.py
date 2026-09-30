import datetime as dt
import json
import os
import random
from dataclasses import dataclass
from decimal import Decimal

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@dataclass
class Txn:
    date: str
    description: str
    amount: Decimal  # +credit, -debit
    balance: Decimal


def make_statement_data(seed: int, opening: Decimal, days: int = 30):
    rng = random.Random(seed)
    bal = opening
    txns = []
    start = dt.date(2025, 1, 1)
    descriptions = [
        "ACH DEPOSIT",
        "STRIPE PAYOUT",
        "PAYROLL",
        "AWS",
        "RENT",
        "LOAN PMT",
        "CARD PURCH",
    ]

    for d in range(days):
        for _ in range(rng.randint(0, 4)):
            amt = Decimal(rng.randint(-400000, 600000)) / 100
            bal += amt
            date_str = str(start + dt.timedelta(days=d))
            txns.append(Txn(date_str, rng.choice(descriptions), amt, bal))

    return {
        "opening": str(opening),
        "closing": str(bal),
        # FIX: Explicitly convert Decimals to strings for JSON serialization
        "txns": [
            {
                "date": t.date,
                "description": t.description,
                "amount": str(t.amount),
                "balance": str(t.balance),
            }
            for t in txns
        ],
    }


def draw_pdf_layout_1(filepath: str, data: dict, bank_name: str):
    """Standard: Date, Description, Amount, Running Balance"""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, f"{bank_name} - Business Checking")
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 1.5 * inch, f"Opening Balance: ${data['opening']}")
    c.drawString(1 * inch, height - 1.7 * inch, f"Closing Balance: ${data['closing']}")

    y = height - 2.5 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Date")
    c.drawString(2 * inch, y, "Description")
    c.drawString(5 * inch, y, "Amount")
    c.drawString(6.5 * inch, y, "Balance")
    c.setFont("Helvetica", 9)
    y -= 0.25 * inch

    for txn in data["txns"]:
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1 * inch, y, "Date")
            c.drawString(2 * inch, y, "Description")
            c.drawString(5 * inch, y, "Amount")
            c.drawString(6.5 * inch, y, "Balance")
            c.setFont("Helvetica", 9)
            y -= 0.25 * inch
        c.drawString(1 * inch, y, txn["date"])
        c.drawString(2 * inch, y, txn["description"])
        c.drawRightString(5.8 * inch, y, f"${txn['amount']}")
        c.drawRightString(7.5 * inch, y, f"${txn['balance']}")
        y -= 0.2 * inch
    c.save()


def draw_pdf_layout_2(filepath: str, data: dict, bank_name: str):
    """Different date format (MM/DD/YY) and separate Debit/Credit columns"""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, height - 1 * inch, f"{bank_name} Statement")
    c.setFont("Helvetica", 10)
    c.drawString(
        1 * inch, height - 1.4 * inch, f"Start: ${data['opening']}  |  End: ${data['closing']}"
    )

    y = height - 2.2 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Date (MM/DD/YY)")
    c.drawString(2.5 * inch, y, "Description")
    c.drawString(4.5 * inch, y, "Debit")
    c.drawString(5.5 * inch, y, "Credit")
    c.setFont("Helvetica", 9)
    y -= 0.25 * inch

    for txn in data["txns"]:
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1 * inch, y, "Date (MM/DD/YY)")
            c.drawString(2.5 * inch, y, "Description")
            c.drawString(4.5 * inch, y, "Debit")
            c.drawString(5.5 * inch, y, "Credit")
            c.setFont("Helvetica", 9)
            y -= 0.25 * inch

        dt_obj = dt.datetime.strptime(txn["date"], "%Y-%m-%d")
        c.drawString(1 * inch, y, dt_obj.strftime("%m/%d/%y"))
        c.drawString(2.5 * inch, y, txn["description"])
        amt = Decimal(txn["amount"])
        if amt < 0:
            c.drawRightString(5.3 * inch, y, f"${abs(amt)}")
        else:
            c.drawRightString(6.3 * inch, y, f"${amt}")
        y -= 0.2 * inch
    c.save()


if __name__ == "__main__":
    os.makedirs("data/synthetic/clean", exist_ok=True)
    os.makedirs("data/synthetic/tampered", exist_ok=True)
    os.makedirs("data/synthetic/wrong_type", exist_ok=True)
    os.makedirs("data/synthetic/truth", exist_ok=True)

    banks = ["Horizon Bank", "Apex Financial", "Meridian Trust", "Valley Credit", "Summit Bancorp"]

    # 60 Clean Statements
    for i in range(60):
        layout_fn = random.choice([draw_pdf_layout_1, draw_pdf_layout_2])
        bank = random.choice(banks)
        data = make_statement_data(seed=i, opening=Decimal(random.randint(10000, 50000)))

        pdf_path = f"data/synthetic/clean/statement_{i:03d}.pdf"
        truth_path = f"data/synthetic/truth/statement_{i:03d}.json"

        layout_fn(pdf_path, data, bank)
        with open(truth_path, "w") as f:
            json.dump({"doc_type": "bank_statement", "is_tampered": False, **data}, f, indent=2)

    # 15 Tampered statements (Change one amount, break the running balance)
    for i in range(60, 75):
        data = make_statement_data(seed=i, opening=Decimal(random.randint(10000, 50000)))
        if data["txns"]:
            idx = random.randint(0, len(data["txns"]) - 1)
            original_amt = Decimal(data["txns"][idx]["amount"])
            data["txns"][idx]["amount"] = str(original_amt + Decimal("12.50"))  # Subtle tamper

        pdf_path = f"data/synthetic/tampered/statement_{i:03d}.pdf"
        truth_path = f"data/synthetic/truth/statement_{i:03d}.json"

        draw_pdf_layout_1(pdf_path, data, random.choice(banks))
        with open(truth_path, "w") as f:
            json.dump({"doc_type": "bank_statement", "is_tampered": True, **data}, f, indent=2)

    # 15 Wrong Type (Invoices)
    for i in range(75, 90):
        pdf_path = f"data/synthetic/wrong_type/doc_{i:03d}.pdf"
        truth_path = f"data/synthetic/truth/doc_{i:03d}.json"

        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, 7 * inch, f"INVOICE #{10000 + i}")
        c.setFont("Helvetica", 12)
        c.drawString(1 * inch, 6.5 * inch, "Acme Corp")
        c.drawString(1 * inch, 6.2 * inch, "Services Rendered: $4,500.00")
        c.save()

        with open(truth_path, "w") as f:
            json.dump({"doc_type": "invoice", "is_tampered": False}, f, indent=2)

    print("✅ Dataset generated: 60 clean, 15 tampered, 15 wrong-type.")
