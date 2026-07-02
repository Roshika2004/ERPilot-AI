# ai_agents/agents/fraud_agent.py

def fraud_agent(claim, memory, ai_result):
    """
    Detect abnormal patterns, anomalies, duplication risk
    """

    fraud_score = ai_result.get("fraud_score", 0)

    # behavior-based boost
    if memory["avg_amount"] > 0:
        deviation = abs(float(claim.amount) - memory["avg_amount"])

        if deviation > memory["avg_amount"] * 2:
            fraud_score += 20

    # high frequency risk
    if memory["total_claims"] > 10:
        fraud_score += 10

    return {
        "fraud_score": min(fraud_score, 100),
        "risk_level": "HIGH" if fraud_score > 70 else "MEDIUM" if fraud_score > 40 else "LOW"
    }