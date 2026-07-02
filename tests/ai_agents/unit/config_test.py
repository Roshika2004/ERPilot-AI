"""
conftest.py — shared fixtures for the entire test suite
Place this at your project root (next to manage.py).
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def groq_approve_response():
    """Groq returns a low-fraud-score response."""
    def _make(score=15, confidence=0.90, reasoning="Normal expense."):
        msg = MagicMock()
        msg.content = f"Confidence: {confidence}\nFraud Score: {score}\nReasoning: {reasoning}"
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp
    return _make


@pytest.fixture
def groq_fraud_response():
    """Groq returns a high-fraud-score response."""
    def _make(score=92, confidence=0.95, reasoning="Duplicate receipt detected."):
        msg = MagicMock()
        msg.content = f"Confidence: {confidence}\nFraud Score: {score}\nReasoning: {reasoning}"
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp
    return _make


@pytest.fixture
def normal_memory():
    return {
        "total_claims": 3,
        "avg_amount": 1500.0,
        "high_value_count": 0,
    }


@pytest.fixture
def high_freq_memory():
    return {
        "total_claims": 18,
        "avg_amount": 3000.0,
        "high_value_count": 6,
    }


@pytest.fixture
def clean_policy():
    return {
        "violation": False,
        "risk_level": "LOW",
        "flags": [],
        "reason": "No violations detected",
    }


@pytest.fixture
def medium_policy():
    return {
        "violation": True,
        "risk_level": "MEDIUM",
        "flags": ["Hotel claim exceeds ₹5000 policy limit"],
        "reason": "Hotel claim exceeds ₹5000 policy limit",
    }


@pytest.fixture
def high_policy():
    return {
        "violation": True,
        "risk_level": "HIGH",
        "flags": ["Food claim exceeds ₹1000 policy limit"],
        "reason": "Food claim exceeds ₹1000 policy limit",
    }


# ---------------------------------------------------------------------------
# FakeClaim fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def make_claim():
    """Factory fixture: make_claim(title, amount, created_at=None)"""
    class FakeClaim:
        def __init__(self, title, amount, created_at=None):
            self.title = title
            self.amount = amount
            self.created_at = created_at
    return FakeClaim
