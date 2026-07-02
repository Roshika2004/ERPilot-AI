from claims.models import Claim

def get_employee_memory(employee_id):

    claims = Claim.objects.filter(employee_id=employee_id)

    total_claims = claims.count()

    if total_claims == 0:
        return {

            "avg_amount": 0,
            "total_claims": 0,
            "high_value_count": 0,
            "duplicate_invoice": False,
            "is_first_claim": True,
        }

    total_amount = sum(c.amount for c in claims)
    avg_amount = round(total_amount / total_claims, 1)

    high_value_count = claims.filter(amount__gt=5000).count()

    return {
        "avg_amount": avg_amount,
        "total_claims": total_claims,
        "high_value_count": high_value_count,
        "duplicate_invoice": False,
        "is_first_claim": total_claims == 1,
    }