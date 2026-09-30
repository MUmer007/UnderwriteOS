from decimal import Decimal

import pytest
from pydantic import ValidationError

from uw.guardrails.numbers import check_memo
from uw.llm.schemas import StatementOut
from uw.risk.reconcile import reconcile


class TestMalformedInput:
    """Tests that the system handles malformed input gracefully."""

    def test_schema_rejects_invalid_json(self):
        """Pydantic schema should reject invalid JSON."""
        bad_json = '{"is_bank_statement": "not_a_boolean", "transactions": "not_a_list"}'
        with pytest.raises(ValidationError):
            StatementOut.model_validate_json(bad_json)
        print("? Schema correctly rejects invalid JSON")

    def test_schema_rejects_missing_required_fields(self):
        """Pydantic schema should reject JSON missing required fields."""
        bad_json = '{"bank_name": "Test"}'  # missing is_bank_statement
        with pytest.raises(ValidationError):
            StatementOut.model_validate_json(bad_json)
        print("? Schema correctly rejects missing required fields")

    def test_reconcile_handles_empty_transactions(self):
        """Reconciliation should handle empty transaction list."""
        is_valid, diff = reconcile(Decimal("1000"), Decimal("1000"), [])
        assert is_valid is True
        assert diff == Decimal("0")
        print("? Reconciliation handles empty transactions")

    def test_reconcile_handles_negative_balances(self):
        """Reconciliation should handle negative balances."""
        is_valid, diff = reconcile(Decimal("-500"), Decimal("-1000"), [Decimal("-500")])
        assert is_valid is True
        print("? Reconciliation handles negative balances")

    def test_guardrail_handles_empty_memo(self):
        """Guardrail should handle empty memo gracefully."""
        violations = check_memo("", set())
        assert violations == []
        print("? Guardrail handles empty memo")

    def test_guardrail_handles_unicode(self):
        """Guardrail should handle unicode in memo without crashing."""
        # Using unicode escapes (\u20ac = Euro, \u00a5 = Yen) to avoid encoding issues
        violations = check_memo(
            "Balance: \u20ac1.000,50 | \u00a5100", {Decimal("1000.50"), Decimal("100")}
        )
        assert isinstance(violations, list)
        print("? Guardrail handles unicode")


class TestEdgeCases:
    """Tests edge cases in the risk engine."""

    def test_dscr_zero_debt_service(self):
        """DSCR should return Infinity when debt service is zero."""
        from uw.risk.engine import dscr

        result = dscr(Decimal("1000"), Decimal("0"))
        assert result == Decimal("Infinity")
        print("? DSCR handles zero debt service")

    def test_average_daily_balance_empty(self):
        """Average daily balance should return 0 for empty list."""
        from uw.risk.engine import average_daily_balance

        result = average_daily_balance([])
        assert result == Decimal("0")
        print("? Average daily balance handles empty list")

    def test_revenue_volatility_insufficient_data(self):
        """Revenue volatility should return Infinity with < 3 months."""
        from uw.risk.engine import revenue_volatility

        result = revenue_volatility([Decimal("100"), Decimal("200")])
        assert result == Decimal("Infinity")
        print("? Revenue volatility handles insufficient data")
