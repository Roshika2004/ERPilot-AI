"""
Integration Tests — Full AI Claim Pipeline
Tests the complete flow: check_policy -> analyze_claim -> decision_engine -> explainer

These tests mock only external I/O (Groq API, employee memory) but wire all
internal modules together — so real logic in all four files runs end-to-end.

NOTE on confidence scale: decision_engine() and explain_decision() both compare
confidence on a 0-100 scale (`confidence >= 80`, `confidence < 60`), not 0-1.
All mocked Groq responses below use whole numbers 0-100 to match the prompt
spec ("Confidence: <0-100>") and the real comparisons in the code.

NOTE on check_policy() vs policy_engine(): claim_analyzer uses check_policy(),
which only sets violation=True from direct claim-level checks (amount limits,
invoice mismatch, weekend date). Memory-derived risk (frequency, duplicate
invoice flag, etc.) can raise risk_level from LOW to MEDIUM but never sets
violation=True by itself in check_policy. (policy_engine(), the separate
standalone function, behaves differently -- see Scenario 9.)
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


def make_groq_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class FakeClaim:
    def __init__(self, title, amount, created_at=None):
        self.title = title
        self.amount = amount
        self.created_at = created_at


MEMORY_NORMAL = {
    "total_claims": 3,
    "avg_amount": 1500.0,
    "high_value_count": 0,
    "duplicate_invoice": False,
    "is_first_claim": False,
}

MEMORY_HIGH_FREQ = {
    "total_claims": 30,
    "avg_amount": 15000.0,
    "high_value_count": 6,
    "duplicate_invoice": False,
    "is_first_claim": False,
}


class TestCleanClaimApproved:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_low_risk_taxi_approved_end_to_end(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 90\nFraud Score: 15\nReasoning: Normal taxi expense, consistent history."
        )
        from ai_agents.claim_analyzer import analyze_claim
        from ai_agents.explainer import explain_decision

        result = analyze_claim("Taxi ride", 300, employee_id=1)

        assert result["final_decision"] == "APPROVE"
        assert result["fraud_score"] < 50

        explanation = explain_decision(
            "Taxi ride", 300,
            fraud_score=result["fraud_score"],
            confidence=result["confidence"]
        )
        assert explanation["risk_level"] == "LOW"
        assert result["policy"]["violation"] is False


class TestHotelPolicyBlock:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_hotel_over_5000_goes_to_reject(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 80\nFraud Score: 20\nReasoning: Legitimate hotel booking."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Hotel accommodation", 7500, employee_id=2)

        assert result["final_decision"] == "REJECT"
        assert result["policy"]["violation"] is True
        assert result["policy"]["risk_level"] =="HIGH"
        assert any("Hotel" in f for f in result["policy"]["flags"])


class TestFoodHighRiskReject:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_food_over_2000_rejected_by_policy(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 70\nFraud Score: 30\nReasoning: Slightly elevated but within norms."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Food and entertainment", 2500, employee_id=3)

        assert result["final_decision"] == "REJECT"
        assert result["policy"]["risk_level"] == "HIGH"


class TestAIFraudDetection:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_ai_high_fraud_score_rejects(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 95\nFraud Score: 92\nReasoning: Duplicate receipt pattern, inflated amount."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Miscellaneous expense", 400, employee_id=4)

        assert result["final_decision"] == "REJECT"
        assert result["fraud_score"] >= 90
        assert result["policy"]["violation"] is False


class TestAIMediumFraudManualReview:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_medium_fraud_score_triggers_review(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 60\nFraud Score: 65\nReasoning: Unusual amount for category."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Office supplies", 800, employee_id=5)

        assert result["final_decision"] == "MANUAL_REVIEW"
        assert 50 <= result["fraud_score"] < 90


class TestHighFrequencyClaimant:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_HIGH_FREQ)
    def test_high_risk_memory_raises_risk_level_but_ai_drives_decision(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 75\nFraud Score: 30\nReasoning: Slightly above average frequency."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Taxi", 300, employee_id=6)

        assert result["policy"]["risk_level"] == "MEDIUM"
        assert result["policy"]["violation"] is False
        assert result["final_decision"] == "APPROVE"


class TestGroqAPIFailure:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_api_timeout_falls_back_to_computed_values(self, mock_mem, mock_client):
        mock_client.chat.completions.create.side_effect = TimeoutError("Groq is down")

        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Flight booking", 8000, employee_id=7)

        assert result["final_decision"] == "APPROVE"
        assert result["fraud_score"] == 5
        assert result["confidence"] == 100
        assert "policy" in result

    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_api_error_response_is_safe_string(self, mock_mem, mock_client):
        mock_client.chat.completions.create.side_effect = RuntimeError("Auth failed")

        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Hotel", 3000, employee_id=7)

        assert isinstance(result["ai_response"], str)
        assert isinstance(result["reasoning"], str)

    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_api_error_with_policy_violation_forces_reject(self, mock_mem, mock_client):
        mock_client.chat.completions.create.side_effect = RuntimeError("Auth failed")

        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Hotel accommodation", 7500, employee_id=7)

        assert result["final_decision"] == "REJECT"


class TestFlightPolicyBlock:
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_flight_over_approve_limit_is_reject(self, mock_mem, mock_client):
        mock_client.chat.completions.create.return_value = make_groq_response(
            "Confidence: 80\nFraud Score: 25\nReasoning: Flight is within reasonable travel range."
        )
        from ai_agents.claim_analyzer import analyze_claim

        result = analyze_claim("Flight ticket to Mumbai", 15000, employee_id=8)

        assert result["final_decision"] == "REJECT"
        assert result["policy"]["violation"] is True


class TestPolicyEngineStandaloneIntegration:
    def test_policy_engine_with_full_history(self):
        from ai_agents.policy_engine import policy_engine

        saturday = datetime(2024, 1, 6)
        claim = FakeClaim("Hotel accommodation", 8000, created_at=saturday)
        history = {"duplicate_invoice": False, "total_claims": 12}

        result = policy_engine(claim, employee_history=history)

        assert result["violation"] is True
        assert len(result["flags"]) >= 2
        assert result["decision"] in ("MANUAL_REVIEW", "REJECT")

    def test_decision_engine_with_explain_decision(self):
        from ai_agents.decision_engine import decision_engine
        from ai_agents.explainer import explain_decision

        fraud_score = 75
        confidence = 85
        decision = decision_engine(fraud_score, confidence)
        explanation = explain_decision("Hotel", 5000, fraud_score, confidence)

        assert decision == "MANUAL_REVIEW"
        assert explanation["risk_level"] == "HIGH"
        assert "fraud" in explanation["summary"].lower()
        assert "High amount" not in explanation["summary"]


class TestPipelineConsistency:
    @pytest.mark.parametrize("title,amount,ai_resp,expected_decision", [
        ("Taxi", 300, "Confidence: 90\nFraud Score: 10\nReasoning: Clean.", "APPROVE"),
        ("Hotel stay", 7000, "Confidence: 90\nFraud Score: 10\nReasoning: Legit.", "REJECT"),
        ("Food expense", 2500, "Confidence: 90\nFraud Score: 10\nReasoning: Legit.", "REJECT"),
        ("Flight", 15000, "Confidence: 90\nFraud Score: 10\nReasoning: Work trip.", "REJECT"),
    ])
    @patch("ai_agents.claim_analyzer.client")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MEMORY_NORMAL)
    def test_each_policy_category(self, mock_mem, mock_client,
                                  title, amount, ai_resp, expected_decision):
        mock_client.chat.completions.create.return_value = make_groq_response(ai_resp)

        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim(title, amount, employee_id=1)
        assert result["final_decision"] == expected_decision, (
            f"For '{title}' ₹{amount}: expected {expected_decision}, "
            f"got {result['final_decision']} (policy={result['policy']})"
        )