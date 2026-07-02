# ai_agents/agents/finance_agent.py

def finance_agent(claim, memory):
    amount = float(claim.amount)

    avg = memory["avg_amount"]

    score = 0

    # deviation from normal spending
    if avg > 0:
        if amount > avg * 2:
            score += 30
        elif amount < avg * 0.5:
            score += 10

    # category rules
    title = claim.title.lower()

    if "travel" in title:
        if amount > 10000:
            score += 30

    if "hotel" in title and amount > 8000:
        score += 25

    return {
        "finance_score": min(score, 100),
        "budget_flag": "OVER_LIMIT" if score > 50 else "OK"
    }