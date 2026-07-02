"""
Unit Tests — decision_engine.py + explainer.py

IMPORTANT: decision_engine() compares confidence on a 0-100 scale
(`confidence >= 80`), NOT a 0-1 probability. All confidence values below
use the 0-100 scale to match the real comparison.
"""
import pytest


# ===========================================================================
# decision_engine()
# ===========================================================================

class TestDecisionEngineReject:
    """High fraud (>=90) + high confidence (>=80) → REJECT"""

    def test_max_score_max_confidence_rejects(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(100, 100) == "REJECT"

    def test_exact_threshold_rejects(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(90, 80) == "REJECT"

    def test_score_90_confidence_79_not_reject(self):
        """Confidence just below threshold → not REJECT (falls to MANUAL_REVIEW)"""
        from ai_agents.decision_engine import decision_engine
        result = decision_engine(90, 79)
        assert result != "REJECT"
        assert result == "MANUAL_REVIEW"

    def test_score_89_confidence_90_not_reject(self):
        """Score just below threshold → not REJECT (falls to MANUAL_REVIEW)"""
        from ai_agents.decision_engine import decision_engine
        result = decision_engine(89, 90)
        assert result != "REJECT"
        assert result == "MANUAL_REVIEW"

    def test_score_95_confidence_85_rejects(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(95, 85) == "REJECT"


class TestDecisionEngineManualReview:
    """Medium fraud score (50-89) → MANUAL_REVIEW, regardless of confidence"""

    def test_score_50_triggers_review(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(50, 50) == "MANUAL_REVIEW"

    def test_score_75_triggers_review(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(75, 30) == "MANUAL_REVIEW"

    def test_score_89_triggers_review(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(89, 99) == "MANUAL_REVIEW"

    def test_score_90_low_confidence_triggers_review(self):
        """High score but confidence below 80 → not REJECT → MANUAL_REVIEW"""
        from ai_agents.decision_engine import decision_engine
        result = decision_engine(90, 50)
        assert result == "MANUAL_REVIEW"


class TestDecisionEngineApprove:
    """Low fraud score (<50) → APPROVE, regardless of confidence"""

    def test_score_0_approves(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(0, 0) == "APPROVE"

    def test_score_49_approves(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(49, 99) == "APPROVE"

    def test_score_25_low_confidence_approves(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(25, 10) == "APPROVE"

    def test_score_0_high_confidence_approves(self):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(0, 100) == "APPROVE"


class TestDecisionEngineBoundaries:
    """Explicit boundary/edge case tests"""

    @pytest.mark.parametrize("score,conf,expected", [
        (90,  80,  "REJECT"),         # exact REJECT boundary
        (90,  79,  "MANUAL_REVIEW"),  # just under confidence threshold
        (89,  80,  "MANUAL_REVIEW"),  # just under score threshold
        (50,  0,   "MANUAL_REVIEW"),  # lower MANUAL_REVIEW boundary
        (49,  100, "APPROVE"),        # just under MANUAL_REVIEW
        (0,   0,   "APPROVE"),        # absolute minimum
        (100, 100, "REJECT"),         # absolute maximum
    ])
    def test_boundary(self, score, conf, expected):
        from ai_agents.decision_engine import decision_engine
        assert decision_engine(score, conf) == expected

    def test_returns_string(self):
        from ai_agents.decision_engine import decision_engine
        result = decision_engine(50, 50)
        assert isinstance(result, str)

    def test_only_valid_decisions_returned(self):
        from ai_agents.decision_engine import decision_engine
        valid = {"APPROVE", "MANUAL_REVIEW", "REJECT"}
        for score in range(0, 101, 10):
            for conf in [0, 50, 80, 100]:
                result = decision_engine(score, conf)
                assert result in valid, f"Invalid decision '{result}' for score={score}, conf={conf}"


# ===========================================================================
# explain_decision()
#
# amount > 5000           -> "High amount expense"
# fraud_score > 60         -> "High fraud risk detected"
# confidence < 60          -> "Low AI confidence"  (0-100 scale, same as decision_engine)
# no reasons               -> "Normal expense pattern"
# risk_level: >70 HIGH, >40 MEDIUM (else LOW)  -- based on fraud_score only
# ===========================================================================

class TestExplainDecision:

    def test_high_amount_flagged(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Hotel", 6000, fraud_score=10, confidence=90)
        assert "High amount" in result["summary"]

    def test_amount_at_threshold_not_flagged(self):
        """amount > 5000 is strict, so exactly 5000 should not be flagged."""
        from ai_agents.explainer import explain_decision
        result = explain_decision("Hotel", 5000, fraud_score=10, confidence=90)
        assert "High amount" not in result["summary"]

    def test_high_fraud_score_flagged(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=75, confidence=90)
        assert "fraud" in result["summary"].lower()

    def test_fraud_score_at_threshold_not_flagged(self):
        """fraud_score > 60 is strict, so exactly 60 should not be flagged."""
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=60, confidence=90)
        assert "fraud" not in result["summary"].lower()

    def test_low_confidence_flagged(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=10, confidence=30)
        assert "confidence" in result["summary"].lower()

    def test_confidence_at_threshold_not_flagged(self):
        """confidence < 60 is strict, so exactly 60 should not be flagged."""
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=10, confidence=60)
        assert "confidence" not in result["summary"].lower()

    def test_normal_pattern_no_flags(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=10, confidence=90)
        assert result["summary"] == "Normal expense pattern"

    def test_multiple_flags_joined(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Hotel", 6000, fraud_score=75, confidence=30)
        assert "|" in result["summary"]
        assert "High amount" in result["summary"]
        assert "fraud" in result["summary"].lower()
        assert "confidence" in result["summary"].lower()

    def test_risk_level_high(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=80, confidence=90)
        assert result["risk_level"] == "HIGH"

    def test_risk_level_medium(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=50, confidence=90)
        assert result["risk_level"] == "MEDIUM"

    def test_risk_level_low(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=10, confidence=90)
        assert result["risk_level"] == "LOW"

    def test_return_keys_present(self):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=10, confidence=90)
        assert "summary" in result
        assert "risk_level" in result

    @pytest.mark.parametrize("score,expected_level", [
        (71,  "HIGH"),
        (70,  "MEDIUM"),   # boundary: >70 = HIGH, so 70 = MEDIUM
        (41,  "MEDIUM"),
        (40,  "LOW"),
        (0,   "LOW"),
        (100, "HIGH"),
    ])
    def test_risk_level_boundaries(self, score, expected_level):
        from ai_agents.explainer import explain_decision
        result = explain_decision("Taxi", 300, fraud_score=score, confidence=90)
        assert result["risk_level"] == expected_level
