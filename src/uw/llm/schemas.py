from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import List, Optional

class TxnOut(BaseModel):
    date: date
    description: str
    amount: Decimal = Field(description="Positive for credits/deposits, negative for debits/withdrawals")
    balance: Optional[Decimal] = Field(default=None, description="Running balance after this transaction, if present")

class StatementOut(BaseModel):
    is_bank_statement: bool = Field(description="True if this document is a bank statement, false otherwise")
    bank_name: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    transactions: List[TxnOut] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0, description="LLM's self-reported confidence in this extraction")