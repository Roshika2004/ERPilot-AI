"""
Unit Tests — claim_analyzer.py
Covers: analyze_claim(), extract_number(), extract_reasoning(),
        _normalize_confidence(), _format_amount()
All external calls (Groq API, memory, policy) are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

def make_groq_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


MOCK_MEMORY = {
    "total_claims": 3,
    "avg_amount": 2000.0,
    "high_value_count": 1,
    "is_first_claim": False,
    "duplicate_invoice": False,
}

MOCK_POLICY_CLEAN = {
    "violation": False,
    "risk_level": "LOW",
    "flags": [],
    "reason": "No violations detected",
}

MOCK_POLICY_HIGH = {
    "violation": True,
    "risk_level": "HIGH",
    "flags": ["Food claim exceeds policy limit"],
    "reason": "Food claim exceeds policy limit",
}

MOCK_POLICY_MEDIUM = {
    "violation": True,
    "risk_level": "MEDIUM",
    "flags": ["Hotel claim exceeds policy limit"],
    "reason": "Hotel claim exceeds policy limit",
}

MOCK_POLICY_INVOICE_MISMATCH = {
    "violation": True,
    "risk_level": "MEDIUM",
    "flags": ["Invoice total mismatch"],
    "reason": "Invoice total mismatch",
}

AI_RESPONSE_NORMAL = """\
Confidence: 85
Fraud Score: 20
Reasoning: No suspicious patterns detected. Normal claiming history.
"""

AI_RESPONSE_FRAUD = """\
Confidence: 92
Fraud Score: 95
Reasoning: Duplicate receipt pattern detected with inflated amounts.
"""

AI_RESPONSE_MALFORMED = "Something went wrong and the model returned garbage."


# ===========================================================================
# _format_amount()
# ===========================================================================

class TestFormatAmount:

    def test_integer_formatted_to_one_decimal(self):
        from ai_agents.claim_analyzer import _format_amount
        assert _format_amount(500) == "500.0"

    def test_float_formatted_to_one_decimal(self):
        from ai_agents.claim_analyzer import _format_amount
        assert _format_amount(1234.567) == "1234.6"

    def test_string_number_formatted(self):
        from ai_agents.claim_analyzer import _format_amount
        assert _format_amount("300") == "300.0"

    def test_none_returns_string(self):
        from ai_agents.claim_analyzer import _format_amount
        result = _format_amount(None)
        assert isinstance(result, str)

    def test_invalid_string_returns_original(self):
        from ai_agents.claim_analyzer import _format_amount
        result = _format_amount("not-a-number")
        assert isinstance(result, str)

    def test_zero_formatted(self):
        from ai_agents.claim_analyzer import _format_amount
        assert _format_amount(0) == "0.0"


# ===========================================================================
# _normalize_confidence()
# ===========================================================================

class TestNormalizeConfidence:

    def test_decimal_probability_scaled_up(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(0.92) == 92.0

    def test_one_scaled_to_100(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(1.0) == 100.0

    def test_whole_number_unchanged(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(85) == 85.0

    def test_zero_returns_zero(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(0) == 0.0

    def test_value_clamped_to_100(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(150) == 100.0

    def test_negative_clamped_to_zero(self):
        from ai_agents.claim_analyzer import _normalize_confidence
        assert _normalize_confidence(-10) == 0.0

    def test_decimal_drift_makes_reject_reachable(self):
        """Core bug guard: if model returns 0.95 instead of 95,
        normalizing must produce a value that passes >= 80 in decision_engine."""
        from ai_agents.claim_analyzer import _normalize_confidence
        from ai_agents.decision_engine import decision_engine
        confidence = _normalize_confidence(0.95)
        assert decision_engine(92, confidence) == "REJECT"


# ===========================================================================
# extract_number()
# ===========================================================================

class TestExtractNumber:

    def test_extracts_fraud_score(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Fraud Score: 75\nConfidence: 0.9", "Fraud Score") == 75.0

    def test_extracts_confidence(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Confidence: 0.85\nFraud Score: 40", "Confidence") == 0.85

    def test_case_insensitive(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("fraud score: 55", "Fraud Score") == 55.0

    def test_missing_field_returns_zero(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Nothing here", "Fraud Score") == 0

    def test_decimal_value(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Confidence: 0.923", "Confidence") == 0.923

    def test_integer_value(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Fraud Score: 100", "Fraud Score") == 100.0

    def test_empty_string_returns_zero(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("", "Fraud Score") == 0

    def test_extra_whitespace_handled(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number("Fraud Score :   88", "Fraud Score") == 88.0

    def test_none_input_returns_zero(self):
        from ai_agents.claim_analyzer import extract_number
        assert extract_number(None, "Confidence") == 0


# ===========================================================================
# extract_reasoning()
# ===========================================================================

class TestExtractReasoning:

    def test_extracts_reasoning(self):
        from ai_agents.claim_analyzer import extract_reasoning
        text = "Confidence: 0.9\nFraud Score: 20\nReasoning: All looks normal."
        assert extract_reasoning(text) == "All looks normal."

    def test_multiline_reasoning_captured(self):
        from ai_agents.claim_analyzer import extract_reasoning
        result = extract_reasoning("Reasoning: Line one\nLine two\nLine three")
        assert "Line one" in result

    def test_missing_reasoning_returns_default(self):
        from ai_agents.claim_analyzer import extract_reasoning
        assert extract_reasoning("No reasoning here") == "No reasoning provided."

    def test_empty_string_returns_default(self):
        from ai_agents.claim_analyzer import extract_reasoning
        assert extract_reasoning("") == "No reasoning provided."

    def test_case_insensitive(self):
        from ai_agents.claim_analyzer import extract_reasoning
        assert extract_reasoning("reasoning: looks clean") == "looks clean"

    def test_none_input_returns_default(self):
        from ai_agents.claim_analyzer import extract_reasoning
        assert extract_reasoning(None) == "No reasoning provided."


# ===========================================================================
# analyze_claim() — happy path
# ===========================================================================

@patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
@patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
@patch("ai_agents.claim_analyzer.client")
class TestAnalyzeClaimHappyPath:

    def test_returns_required_keys(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi ride", 300, employee_id=1)
        for key in ("ai_response", "fraud_score", "confidence", "confidence_percent",
                    "reasoning", "final_decision", "policy"):
            assert key in result, f"Missing key: {key}"

    def test_low_fraud_score_approves(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi ride", 300, employee_id=1)
        assert result["final_decision"] == "APPROVE"
        assert result["fraud_score"] == 20.0
        assert result["confidence"] == 85.0

    def test_confidence_percent_formatted(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi ride", 300, employee_id=1)
        assert result["confidence_percent"] == "85.0%"

    def test_reasoning_extracted(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi ride", 300, employee_id=1)
        assert "Normal" in result["reasoning"]

    def test_policy_returned_in_result(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi ride", 300, employee_id=1)
        assert result["policy"] == MOCK_POLICY_CLEAN

    def test_high_fraud_score_triggers_reject(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_FRAUD)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Duplicate receipt", 5000, employee_id=1)
        assert result["final_decision"] == "REJECT"
        assert result["fraud_score"] == 95.0


# ===========================================================================
# analyze_claim() — POLICY OVERRIDE TESTS
#
# The current claim_analyzer.py uses a simplified rule:
#   if policy["violation"]: final_decision = "REJECT"  ← ALL violations
#   else: final_decision = decision_engine(...)
#
# There is NO invoice-mismatch exception. Any violation → REJECT.
# ===========================================================================

class TestAnalyzeClaimPolicyOverride:

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_HIGH)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_high_risk_policy_forces_reject(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Food expense", 1500, employee_id=1)
        assert result["final_decision"] == "REJECT"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_MEDIUM)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_medium_risk_policy_also_forces_reject(self, mock_client, mock_mem, mock_policy):
        """MEDIUM risk with violation=True → REJECT (no middle path)"""
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Hotel stay", 6000, employee_id=1)
        assert result["final_decision"] == "REJECT"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_INVOICE_MISMATCH)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_invoice_mismatch_violation_also_rejects(self, mock_client, mock_mem, mock_policy):
        """Invoice mismatch sets violation=True → REJECT (no special exception)"""
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["final_decision"] == "REJECT"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_no_violation_uses_ai_decision(self, mock_client, mock_mem, mock_policy):
        """No policy violation → AI decision engine drives the result"""
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["final_decision"] == "APPROVE"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_ai_reject_on_clean_policy(self, mock_client, mock_mem, mock_policy):
        """High AI fraud score with clean policy → AI drives REJECT"""
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_FRAUD)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Miscellaneous", 400, employee_id=1)
        assert result["final_decision"] == "REJECT"
        assert result["policy"]["violation"] is False


# ===========================================================================
# analyze_claim() — FAILURE / FALLBACK TESTS
#
# For MOCK_POLICY_CLEAN (risk_level="LOW", no flags) + MOCK_MEMORY
# (total_claims=3, no duplicate_invoice):
#   _fallback_confidence  → 100
#   _fallback_fraud_score → 5
# Except-block: violation=False + risk_level="LOW" → "APPROVE"
# ===========================================================================

class TestAnalyzeClaimFailures:

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_groq_timeout_falls_back_to_computed_values(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.side_effect = TimeoutError("Groq timeout")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["fraud_score"] == 5
        assert result["confidence"] == 100
        assert result["final_decision"] == "APPROVE"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_connection_error_falls_back(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.side_effect = ConnectionError("No internet")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["final_decision"] == "APPROVE"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_HIGH)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_error_with_policy_violation_forces_reject(self, mock_client, mock_mem, mock_policy):
        """Except-block: violation=True → REJECT regardless of risk_level"""
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Food expense", 1500, employee_id=1)
        assert result["final_decision"] == "REJECT"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_MEDIUM)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_error_with_medium_violation_also_rejects(self, mock_client, mock_mem, mock_policy):
        """Except-block: MEDIUM violation=True → REJECT (not MANUAL_REVIEW)"""
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Hotel stay", 6000, employee_id=1)
        assert result["final_decision"] == "REJECT"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_malformed_ai_response_uses_fallback_values(self, mock_client, mock_mem, mock_policy):
        """Garbage AI response → fallback computes real values, not zeros"""
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_MALFORMED)
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["fraud_score"] == 5
        assert result["confidence"] == 100
        assert result["confidence_percent"] == "100%"
        assert result["reasoning"] == "Normal claim pattern with no suspicious indicators."
        assert result["final_decision"] == "APPROVE"

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_error_result_contains_policy(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert "policy" in result
        assert result["policy"] == MOCK_POLICY_CLEAN

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_error_ai_response_is_string(self, mock_client, mock_mem, mock_policy):
        mock_client.chat.completions.create.side_effect = RuntimeError("Auth failed")
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Hotel", 3000, employee_id=1)
        assert isinstance(result["ai_response"], str)
        assert isinstance(result["reasoning"], str)

    @patch("ai_agents.claim_analyzer.check_policy", return_value={
        "violation": False,
        "risk_level": "LOW",
        "flags": ["Weekend claim submission detected"],
        "reason": "Weekend claim submission detected",
    })
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_fallback_confidence_decreases_for_weekend_flag(self, mock_client, mock_mem, mock_policy):
        """Weekend flag in policy.flags:
           _fallback_confidence: 100 - 5 (weekend) = 95
           _fallback_fraud_score: 5 (base) + 5 (weekend) = 10
           total_claims=3 so the reset-to-5 condition doesn't apply"""
        mock_client.chat.completions.create.return_value = make_groq_response(
            # Omit Reasoning so extract_reasoning returns "No reasoning provided."
            # which triggers fallback reasoning containing the policy reason ("Weekend...")
            "Confidence: 0\nFraud Score: 0"
        )
        from ai_agents.claim_analyzer import analyze_claim
        result = analyze_claim("Taxi", 300, employee_id=1)
        assert result["confidence"] == 95
        assert result["fraud_score"] == 10
        assert "Weekend" in result["reasoning"]


# ===========================================================================
# analyze_claim() — MEMORY INTEGRATION
# ===========================================================================

class TestAnalyzeClaimMemory:

    @patch("ai_agents.claim_analyzer.check_policy", return_value=MOCK_POLICY_CLEAN)
    @patch("ai_agents.claim_analyzer.get_employee_memory")
    @patch("ai_agents.claim_analyzer.client")
    def test_memory_called_with_correct_employee_id(self, mock_client, mock_mem, mock_policy):
        mock_mem.return_value = MOCK_MEMORY
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        analyze_claim("Taxi", 300, employee_id=42)
        mock_mem.assert_called_once_with(42)

    @patch("ai_agents.claim_analyzer.check_policy")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_policy_called_with_correct_kwargs(self, mock_client, mock_mem, mock_policy):
        mock_policy.return_value = MOCK_POLICY_CLEAN
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        analyze_claim("Food expense", 1500, employee_id=7)
        mock_policy.assert_called_once_with(
            employee_id=7,
            title="Food expense",
            amount=1500,
            invoice_amount=None,
            claim_date=None,
            employee_history=MOCK_MEMORY,
        )

    @patch("ai_agents.claim_analyzer.check_policy")
    @patch("ai_agents.claim_analyzer.get_employee_memory", return_value=MOCK_MEMORY)
    @patch("ai_agents.claim_analyzer.client")
    def test_policy_called_with_invoice_and_date(self, mock_client, mock_mem, mock_policy):
        mock_policy.return_value = MOCK_POLICY_CLEAN
        mock_client.chat.completions.create.return_value = make_groq_response(AI_RESPONSE_NORMAL)
        from ai_agents.claim_analyzer import analyze_claim
        analyze_claim(
            "Food expense", 1500, employee_id=7,
            invoice_amount=1450, claim_date="2026-06-15",
        )
        mock_policy.assert_called_once_with(
            employee_id=7,
            title="Food expense",
            amount=1500,
            invoice_amount=1450,
            claim_date="2026-06-15",
            employee_history=MOCK_MEMORY,
        )
