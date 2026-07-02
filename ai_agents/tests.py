from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from ai_agents.decision_engine import decision_engine
from ai_agents.policy_engine import policy_engine


class PolicyEngineTests(TestCase):
    def test_decision_engine_rejects_only_for_high_confidence_fraud(self):
        self.assertEqual(decision_engine(95, 85), "REJECT")
        self.assertEqual(decision_engine(75, 85), "MANUAL_REVIEW")
        self.assertEqual(decision_engine(20, 85), "APPROVE")

    @patch("ai_agents.policy_engine._duplicate_invoice_exists", return_value=False)
    @patch("ai_agents.policy_engine._extract_invoice_date", return_value=None)
    @patch("ai_agents.policy_engine._extract_invoice_amount", return_value=None)
    @patch("ai_agents.policy_engine._extract_text_from_invoice", return_value="")
    def test_missing_invoice_date_does_not_trigger_policy_violation(self, *_):
        claim = SimpleNamespace(
            title="Taxi expense",
            amount=100,
            invoice=object(),
            created_at=None,
        )

        policy = policy_engine(claim, employee_history={})

        self.assertFalse(policy["violation"])
        self.assertIn("Invoice date could not be extracted", policy["reason"])

    @patch("ai_agents.policy_engine._duplicate_invoice_exists", return_value=True)
    @patch("ai_agents.policy_engine._extract_invoice_date", return_value=None)
    @patch("ai_agents.policy_engine._extract_invoice_amount", return_value=100)
    @patch("ai_agents.policy_engine._extract_text_from_invoice", return_value="")
    def test_duplicate_invoice_routes_to_manual_review(self, *_):
        claim = SimpleNamespace(
            title="Taxi expense",
            amount=100,
            invoice=object(),
            created_at=None,
        )

        policy = policy_engine(claim, employee_history={})

        self.assertTrue(policy["violation"])
        self.assertEqual(policy["decision"], "MANUAL_REVIEW")
        self.assertIn("Duplicate invoice detected", policy["reason"])

    @patch("ai_agents.policy_engine._duplicate_invoice_exists", return_value=False)
    @patch("ai_agents.policy_engine._extract_invoice_date", return_value=None)
    @patch("ai_agents.policy_engine._extract_invoice_amount", return_value=95)
    @patch("ai_agents.policy_engine._extract_text_from_invoice", return_value="")
    def test_amount_mismatch_routes_to_manual_review(self, *_):
        claim = SimpleNamespace(
            title="Taxi expense",
            amount=100,
            invoice=object(),
            created_at=None,
        )

        policy = policy_engine(claim, employee_history={})

        self.assertTrue(policy["violation"])
        self.assertEqual(policy["decision"], "MANUAL_REVIEW")
        self.assertIn("Invoice amount mismatch", policy["reason"])

    @patch("ai_agents.policy_engine._duplicate_invoice_exists", return_value=True)
    @patch("ai_agents.policy_engine._extract_invoice_date", return_value=None)
    @patch("ai_agents.policy_engine._extract_invoice_amount", return_value=100)
    @patch("ai_agents.policy_engine._extract_text_from_invoice", return_value="")
    def test_duplicate_invoice_prefers_clear_reason_when_date_is_missing(self, *_):
        claim = SimpleNamespace(
            title="Taxi expense",
            amount=100,
            invoice=object(),
            created_at=None,
        )

        policy = policy_engine(claim, employee_history={})

        self.assertTrue(policy["violation"])
        self.assertEqual(policy["decision"], "MANUAL_REVIEW")
        self.assertIn("Duplicate invoice detected", policy["reason"])
        self.assertNotIn("Invoice date could not be extracted", policy["reason"])
