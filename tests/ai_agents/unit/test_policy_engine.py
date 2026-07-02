"""
Unit Tests — policy_engine.py
Covers: policy_engine(), check_policy()
"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from claims.models import Claim


class FakeClaim:
    def __init__(self, title, amount, created_at=None, invoice_total=None, invoice=None):
        self.title = title
        self.amount = amount
        self.created_at = created_at
        self.invoice = invoice
        if invoice_total is not None:
            self.invoice_total = invoice_total


class TestPolicyEngineHotelRule:
    def test_hotel_under_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel stay", 4999)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_hotel_at_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel stay", 5000)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_hotel_over_approve_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel accommodation", 6000)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True
        assert any("Hotel" in f for f in result["flags"])

    def test_hotel_over_hard_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel accommodation", 11000)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True

    def test_hotel_case_insensitive(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("HOTEL BOOKING", 6000)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True


class TestPolicyEngineFoodRule:
    def test_food_under_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Food and drinks", 999)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_food_over_approve_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Food expense", 1500)
        result = policy_engine(claim)
        assert result["violation"] is True
        assert result["decision"] == "REJECT"
        assert any("Food" in f for f in result["flags"])

    def test_food_over_hard_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Food expense", 2500)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True

    def test_food_at_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Food", 1000)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False


class TestPolicyEngineFlightRule:
    def test_flight_under_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Flight ticket", 9999)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"

    def test_flight_over_approve_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Flight booking", 15000)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True
        assert any("Flight" in f for f in result["flags"])

    def test_flight_over_hard_limit_rejects(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Flight booking", 21000)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True

    def test_flight_at_exact_approve_limit_approves(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Flight", 12000)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False


class TestPolicyEngineInvoiceMismatchRule:
    def test_matching_invoice_no_violation(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300, invoice_total=300)
        result = policy_engine(claim)
        assert result["violation"] is False
        assert result["decision"] == "APPROVE"

    def test_mismatched_invoice_manual_review(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300, invoice_total=450)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_no_invoice_field_treated_as_matched(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        result = policy_engine(claim)
        assert result["violation"] is False
        assert result["decision"] == "APPROVE"


class TestPolicyEngineInvoiceParsingRule:
    def test_text_invoice_prefers_total_keyword_over_receipt_number(self):
        from ai_agents.policy_engine import policy_engine
        invoice = SimpleUploadedFile(
            "invoice.txt",
            b"Invoice Total: 5500\nReceipt No. 1",
            content_type="text/plain",
        )
        claim = FakeClaim("Flight", 5500, invoice=invoice)
        result = policy_engine(claim)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False


class TestPolicyEngineMemoryRiskRule:
    def test_duplicate_invoice_alone_escalates_to_reject(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Office supplies", 500)
        history = {"duplicate_invoice": True}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True
        assert any("Duplicate invoice" in f for f in result["flags"])

    def test_no_duplicate_passes(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Office supplies", 500)
        history = {"duplicate_invoice": False}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_moderate_claim_frequency_alone_does_not_escalate(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        history = {"total_claims": 11}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "APPROVE"
        assert result["violation"] is False
        assert any("frequency" in f.lower() for f in result["flags"])

    def test_exactly_10_claims_no_flag(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        history = {"total_claims": 10}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "APPROVE"
        assert not any("frequency" in f.lower() for f in result["flags"])

    def test_combined_risk_factors_reach_high_and_reject(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        history = {
            "total_claims": 30,
            "high_value_count": 6,
            "avg_amount": 15000,
        }
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "REJECT"
        assert result["violation"] is True

    def test_memory_risk_high_results_in_reject(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        history = {"duplicate_invoice": True, "total_claims": 15}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "REJECT"

    def test_hard_limit_reject_not_downgraded_by_memory(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel accommodation", 11000)
        history = {"duplicate_invoice": True}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "REJECT"

    def test_first_claim_reduces_risk_points(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        history = {"duplicate_invoice": True, "is_first_claim": True}
        result = policy_engine(claim, employee_history=history)
        assert result["decision"] == "APPROVE"
        assert any("First claim" in f for f in result["flags"])


class TestPolicyEngineWeekendRule:
    def test_saturday_claim_triggers_reject(self):
        from ai_agents.policy_engine import policy_engine
        saturday = datetime(2024, 1, 6)
        claim = FakeClaim("Taxi", 300, created_at=saturday)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"
        assert any("Weekend" in f for f in result["flags"])

    def test_sunday_claim_triggers_reject(self):
        from ai_agents.policy_engine import policy_engine
        sunday = datetime(2024, 1, 7)
        claim = FakeClaim("Taxi", 300, created_at=sunday)
        result = policy_engine(claim)
        assert result["decision"] == "REJECT"

    def test_weekday_claim_no_weekend_flag(self):
        from ai_agents.policy_engine import policy_engine
        monday = datetime(2024, 1, 8)
        claim = FakeClaim("Taxi", 300, created_at=monday)
        result = policy_engine(claim)
        assert not any("Weekend" in f for f in result["flags"])

    def test_no_created_at_no_weekend_flag(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300, created_at=None)
        result = policy_engine(claim)
        assert not any("Weekend" in f for f in result["flags"])

    def test_iso_string_created_at_parsed(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300, created_at="2024-01-06T10:00:00")
        result = policy_engine(claim)
        assert any("Weekend" in f for f in result["flags"])


class TestPolicyEngineReturnStructure:
    def test_return_keys_present(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        result = policy_engine(claim)
        for key in ("decision", "flags", "violation", "reason", "action",
                    "expense_type", "memory_risk_level", "is_first_claim"):
            assert key in result, f"Missing key: {key}"

    def test_no_violations_reason_message(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Taxi", 300)
        result = policy_engine(claim)
        assert result["reason"] == "No violations detected"

    def test_multiple_flags_joined_in_reason(self):
        from ai_agents.policy_engine import policy_engine
        saturday = datetime(2024, 1, 6)
        claim = FakeClaim("Hotel stay", 6000, created_at=saturday)
        result = policy_engine(claim)
        assert "|" in result["reason"]
        assert len(result["flags"]) >= 2

    def test_action_matches_decision(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Hotel stay", 6000)
        result = policy_engine(claim)
        assert result["action"] == result["decision"]

    def test_unrecognized_title_has_no_expense_type(self):
        from ai_agents.policy_engine import policy_engine
        claim = FakeClaim("Office supplies", 500)
        result = policy_engine(claim)
        assert result["expense_type"] is None


class TestPolicyEngineReceiptPolicies(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='receipt-user', password='pass1234')

    def test_receipt_amount_mismatch_routes_to_manual_review(self):
        from ai_agents.policy_engine import policy_engine

        claim = FakeClaim("Taxi", 300)
        claim.invoice = SimpleUploadedFile(
            "receipt.txt",
            b"Invoice Total: 350.00",
            content_type="text/plain",
        )

        result = policy_engine(claim)

        assert result["decision"] == "APPROVE"
        assert result["violation"] is False

    def test_duplicate_receipt_for_same_employee_routes_to_manual_review(self):
        from ai_agents.policy_engine import policy_engine

        Claim.objects.create(
            employee=self.user,
            title="Taxi",
            amount="300.00",
            invoice=SimpleUploadedFile(
                "existing-receipt.txt",
                b"Invoice Total: 300.00",
                content_type="text/plain",
            ),
            status="PENDING",
        )

        claim = FakeClaim("Taxi", 300)
        claim.employee = self.user
        claim.invoice = SimpleUploadedFile(
            "existing-receipt.txt",
            b"Invoice Total: 300.00",
            content_type="text/plain",
        )

        result = policy_engine(claim)

        assert result["decision"] == "MANUAL_REVIEW"
        assert result["violation"] is True
        assert any("Duplicate receipt" in flag for flag in result["flags"])


class TestPolicyEngineHelpers:
    def test_coerce_decimal_returns_none_for_invalid_values(self):
        from ai_agents.policy_engine import _coerce_decimal

        assert _coerce_decimal(None) is None
        assert _coerce_decimal("") is None
        assert _coerce_decimal(False) is None
        assert _coerce_decimal("not-a-number") is None

    def test_extract_receipt_amount_from_invoice_text(self):
        from ai_agents.policy_engine import _extract_receipt_amount

        invoice = SimpleUploadedFile(
            "invoice.txt",
            b"Invoice Total: 550.50\nReceipt No: 1",
            content_type="text/plain",
        )
        assert _extract_receipt_amount(invoice) == Decimal("550.50")

    def test_extract_receipt_amount_from_numeric_token(self):
        from ai_agents.policy_engine import _extract_receipt_amount

        invoice = SimpleUploadedFile(
            "invoice.txt",
            b"Total due 750",
            content_type="text/plain",
        )
        assert _extract_receipt_amount(invoice) == Decimal("750")

    def test_invoice_match_status_mismatch_detects_violation(self):
        from ai_agents.policy_engine import _invoice_match_status

        claim = FakeClaim("Taxi", 300, invoice_total=450)
        result = _invoice_match_status(claim)

        assert result["matched"] is False
        assert result["violation"] is True
        assert "entered 300" in result["flag"]

    def test_get_invoice_identity_handles_read_errors(self):
        from ai_agents.policy_engine import _get_invoice_identity

        class BadInvoice:
            name = "bad.txt"

            def read(self):
                raise ValueError("boom")

            def seek(self, pos):
                pass

        result = _get_invoice_identity(BadInvoice())
        assert result["name"] == "bad.txt"
        assert result["signature"] is None

    def test_duplicate_receipt_status_handles_query_exceptions(self):
        from ai_agents.policy_engine import _duplicate_receipt_status

        claim = FakeClaim("Taxi", 300)
        claim.employee = object()
        claim.invoice = SimpleUploadedFile(
            "receipt.txt",
            b"Invoice Total: 300.00",
            content_type="text/plain",
        )

        with patch("ai_agents.policy_engine.Claim.objects.filter", side_effect=Exception("db")):
            result = _duplicate_receipt_status(claim)

        assert result == {"duplicate": False, "flag": None}

    def test_weekend_flag_parses_string_date(self):
        from ai_agents.policy_engine import _weekend_flag

        claim = FakeClaim("Taxi", 300, created_at="2024-01-06T10:00:00")
        assert _weekend_flag(claim) == "Weekend claim submission detected"

    def test_weekend_flag_ignores_invalid_date(self):
        from ai_agents.policy_engine import _weekend_flag

        claim = FakeClaim("Taxi", 300, created_at="not-a-date")
        assert _weekend_flag(claim) is None

    def test_memory_risk_low_with_moderate_frequency(self):
        from ai_agents.policy_engine import _memory_risk, check_policy

        history = {"total_claims": 11}
        memory = _memory_risk(history)
        assert memory["risk_level"] == "LOW"
        assert any("Moderate claim frequency" in flag for flag in memory["flags"])

        result = check_policy(employee_id=1, title="Taxi", amount=300, employee_history=history)
        assert result["risk_level"] == "LOW"
        assert any("Moderate claim frequency" in flag for flag in result["flags"])


class TestCheckPolicy:
    def test_hotel_violation_high_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Hotel stay", amount=6000)
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"
        assert any("Hotel" in f for f in result["flags"])

    def test_hotel_hard_limit_high_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Hotel stay", amount=11000)
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"

    def test_food_violation_high_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Food expense", amount=1500)
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"

    def test_food_hard_limit_high_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Food expense", amount=2500)
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"

    def test_flight_violation_high_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Flight booking", amount=12500)
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"

    def test_no_violation_low_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Taxi", amount=300)
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"
        assert result["reason"] == "No violations detected"

    def test_invoice_mismatch_bumps_to_medium_risk(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, invoice_amount=450,
        )
        assert result["violation"] is True
        assert result["risk_level"] == "MEDIUM"
        assert any("Invoice total mismatch" in f for f in result["flags"])

    def test_matching_invoice_amount_no_violation(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, invoice_amount=300,
        )
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"

    def test_weekend_claim_date_bumps_to_high(self):
        from ai_agents.policy_engine import check_policy
        saturday = "2024-01-06"
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, claim_date=saturday,
        )
        assert result["violation"] is True
        assert result["risk_level"] == "HIGH"
        assert any("Weekend" in f for f in result["flags"])

    def test_weekday_claim_date_no_violation(self):
        from ai_agents.policy_engine import check_policy
        monday = "2024-01-08"
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, claim_date=monday,
        )
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"

    def test_high_memory_risk_bumps_low_to_medium(self):
        from ai_agents.policy_engine import check_policy
        history = {"duplicate_invoice": True}
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, employee_history=history,
        )
        assert result["risk_level"] == "MEDIUM"
        assert any("Duplicate invoice" in f for f in result["flags"])

    def test_high_memory_risk_does_not_downgrade_existing_high(self):
        from ai_agents.policy_engine import check_policy
        history = {"duplicate_invoice": True}
        result = check_policy(
            employee_id=1, title="Hotel stay", amount=11000, employee_history=history,
        )
        assert result["risk_level"] == "HIGH"

    def test_missing_employee_history_defaults_safely(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Taxi", amount=300, employee_history=None)
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"

    def test_invalid_invoice_amount_is_ignored(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, invoice_amount="not-a-number",
        )
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"

    def test_invalid_claim_date_is_ignored(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(
            employee_id=1, title="Taxi", amount=300, claim_date="not-a-date",
        )
        assert result["violation"] is False
        assert result["risk_level"] == "LOW"

    def test_return_keys_present(self):
        from ai_agents.policy_engine import check_policy
        result = check_policy(employee_id=1, title="Taxi", amount=300)
        for key in ("violation", "risk_level", "flags", "reason", "expense_type", "is_first_claim"):
            assert key in result 