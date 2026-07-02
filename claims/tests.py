from django.test import TestCase

from claims.models import Claim
from claims.views import build_policy_review_payload


class PolicyReviewPayloadTests(TestCase):
    def test_manual_review_payload_uses_meaningful_confidence_and_reason(self):
        payload = build_policy_review_payload(
            {"reason": "Duplicate invoice detected for this employee; manual review required", "action": "MANUAL_REVIEW"}
        )

        self.assertEqual(payload["status"], "PENDING")
        self.assertGreater(payload["confidence"], 0)
        self.assertIn("Duplicate invoice detected", payload["reasoning"])

    def test_rejection_payload_is_clear_and_not_zero_confidence(self):
        payload = build_policy_review_payload(
            {"reason": "Suspicious fraud pattern detected", "action": "REJECT"}
        )

        self.assertEqual(payload["status"], "REJECTED")
        self.assertGreater(payload["confidence"], 0)
        self.assertIn("Suspicious fraud pattern", payload["reasoning"])

    def test_display_confidence_falls_back_for_policy_review(self):
        claim = Claim(ai_confidence=0, ai_recommendation="POLICY REVIEW: Duplicate invoice detected")
        self.assertEqual(claim.get_display_ai_confidence(), 60)
