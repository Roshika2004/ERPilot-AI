"""
Unit Tests — memory.py (get_employee_memory)

Real implementation:
    claims = Claim.objects.filter(employee_id=employee_id)
    total_claims = claims.count()
    if total_claims == 0: → return zeros + duplicate_invoice=False + is_first_claim=True
    total_amount = sum(c.amount for c in claims)
    avg_amount = total_amount / total_claims
    high_value_count = claims.filter(amount__gt=5000).count()
    return { avg_amount, total_claims, high_value_count,
             duplicate_invoice=False, is_first_claim=(total_claims == 1) }
"""
from unittest.mock import patch, MagicMock


def make_mock_claims(amounts):
    """
    Build a mock queryset whose:
      - .count()              returns len(amounts)
      - iteration             yields FakeClaim objects with .amount
      - .filter(amount__gt=5000).count()  returns count of amounts > 5000
    """
    class FakeClaim:
        def __init__(self, amount):
            self.amount = amount

    fake_objs = [FakeClaim(a) for a in amounts]

    mock_qs = MagicMock()
    mock_qs.count.return_value = len(amounts)
    mock_qs.__iter__ = MagicMock(return_value=iter(fake_objs))

    # .filter(amount__gt=5000) returns a new queryset
    high_value_qs = MagicMock()
    high_value_qs.count.return_value = sum(1 for a in amounts if a > 5000)
    mock_qs.filter.return_value = high_value_qs

    return mock_qs


EXPECTED_KEYS = {"avg_amount", "total_claims", "high_value_count",
                  "duplicate_invoice", "is_first_claim"}


# ===========================================================================
# BRANCH 1: total_claims == 0  →  early return
# ===========================================================================

class TestGetEmployeeMemoryZeroClaims:

    def test_zero_claims_returns_all_zeros(self):
        """When employee has no claims, all numeric values must be 0,
        duplicate_invoice is False, and is_first_claim is True."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([])
            result = get_employee_memory(employee_id=99)
        assert result == {
            "avg_amount": 0,
            "total_claims": 0,
            "high_value_count": 0,
            "duplicate_invoice": False,
            "is_first_claim": True,
        }

    def test_zero_claims_has_all_keys(self):
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([])
            result = get_employee_memory(employee_id=99)
        for key in EXPECTED_KEYS:
            assert key in result

    def test_zero_claims_filters_by_employee_id(self):
        """filter() must be called with the correct employee_id."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([])
            get_employee_memory(employee_id=42)
        MockClaim.objects.filter.assert_called_once_with(employee_id=42)


# ===========================================================================
# BRANCH 2: total_claims > 0  →  full calculation
# ===========================================================================

class TestGetEmployeeMemoryWithClaims:

    def test_total_claims_count(self):
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000, 3000])
            result = get_employee_memory(employee_id=1)
        assert result["total_claims"] == 3

    def test_avg_amount_calculated_correctly(self):
        """avg = sum([1000, 2000, 3000]) / 3 = 2000.0"""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000, 3000])
            result = get_employee_memory(employee_id=1)
        assert result["avg_amount"] == 2000.0

    def test_avg_amount_single_claim(self):
        """Single claim → avg equals that claim's amount, and is_first_claim is True."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([4500])
            result = get_employee_memory(employee_id=1)
        assert result["avg_amount"] == 4500.0
        assert result["total_claims"] == 1
        assert result["is_first_claim"] is True

    def test_avg_amount_is_rounded_to_one_decimal(self):
        """Average claims should be rounded to one decimal in memory."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000, 4000])
            result = get_employee_memory(employee_id=1)
        assert result["avg_amount"] == 2333.3

    def test_multiple_claims_is_not_first_claim(self):
        """More than one historical claim -> is_first_claim is False."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000])
            result = get_employee_memory(employee_id=1)
        assert result["is_first_claim"] is False

    def test_duplicate_invoice_always_false(self):
        """duplicate_invoice is hardcoded False in this implementation regardless of claim count."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000, 3000])
            result = get_employee_memory(employee_id=1)
        assert result["duplicate_invoice"] is False

    def test_high_value_count_none_above_5000(self):
        """No claims above ₹5000 → high_value_count = 0."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([500, 1000, 4999])
            result = get_employee_memory(employee_id=1)
        assert result["high_value_count"] == 0

    def test_high_value_count_some_above_5000(self):
        """Claims of 6000, 8000 are above ₹5000 → high_value_count = 2."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([500, 6000, 8000])
            result = get_employee_memory(employee_id=1)
        assert result["high_value_count"] == 2

    def test_high_value_count_all_above_5000(self):
        """All claims above ₹5000."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([6000, 7000, 9000])
            result = get_employee_memory(employee_id=1)
        assert result["high_value_count"] == 3

    def test_high_value_threshold_is_5000_exclusive(self):
        """Exactly ₹5000 is NOT high value — filter uses amount__gt=5000."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([5000])
            result = get_employee_memory(employee_id=1)
        # 5000 is not > 5000, so high_value_count must be 0
        assert result["high_value_count"] == 0

    def test_high_value_filter_uses_amount_gt_5000(self):
        """Verify .filter(amount__gt=5000) is the exact call made."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            mock_qs = make_mock_claims([1000, 6000])
            MockClaim.objects.filter.return_value = mock_qs
            get_employee_memory(employee_id=1)
        mock_qs.filter.assert_called_once_with(amount__gt=5000)

    def test_avg_amount_with_decimals(self):
        """Decimal amounts — avg should be precise."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000, 2000])
            result = get_employee_memory(employee_id=1)
        assert result["avg_amount"] == 1500.0

    def test_return_keys_match_exactly(self):
        """Return dict must have exactly these 5 keys — no extras, no missing."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([1000])
            result = get_employee_memory(employee_id=1)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_employee_id_passed_to_filter(self):
        """Each call must filter by the specific employee_id given."""
        from ai_agents.memory import get_employee_memory
        with patch("ai_agents.memory.Claim") as MockClaim:
            MockClaim.objects.filter.return_value = make_mock_claims([500])
            get_employee_memory(employee_id=77)
        MockClaim.objects.filter.assert_called_once_with(employee_id=77)
