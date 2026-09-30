from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class TxnOut(BaseModel):
    date: date
    description: str
    amount: Decimal = Field(
        description="Positive for credits/deposits, negative for debits/withdrawals"
    )
    balance: Decimal | None = Field(
        default=None, description="Running balance after this transaction, if present"
    )


class StatementOut(BaseModel):
    is_bank_statement: bool = Field(
        description="True if this document is a bank statement, false otherwise"
    )
    bank_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    transactions: list[TxnOut] = Field(default_factory=list)
    extraction_confidence: float = Field(
        ge=0.0, le=1.0, description="LLM's self-reported confidence in this extraction"
    )
