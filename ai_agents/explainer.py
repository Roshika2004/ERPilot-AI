def explain_decision(title, amount, fraud_score, confidence):
    reasons = []

    if amount > 5000:
        reasons.append("High amount expense")

    if fraud_score > 60:
        reasons.append("High fraud risk detected")

    if confidence < 60:
        reasons.append("Low AI confidence")

    if not reasons:
        reasons.append("Normal expense pattern")

    return {
        "summary": " | ".join(reasons),
        "risk_level": "HIGH" if fraud_score > 70 else "MEDIUM" if fraud_score > 40 else "LOW"
    }