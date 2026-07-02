from ai_agents.groq_config import client
from ai_agents.decision_engine import decision_engine
from ai_agents.memory import get_employee_memory
from ai_agents.policy_engine import check_policy
import re


def _fallback_confidence(policy, memory):
    confidence = 100

    if policy["risk_level"] == "MEDIUM":
        confidence -= 10
    elif policy["risk_level"] == "HIGH":
        confidence -= 20

    memory_level = memory.get("risk_level", "LOW")

    if memory_level == "MEDIUM":
        confidence -= 5
    elif memory_level == "HIGH":
        confidence -= 10

    if memory.get("duplicate_invoice", False):
        confidence += 5

    if any("Weekend" in flag for flag in policy.get("flags", [])):
        confidence -= 5

    if memory.get("total_claims", 0) <= 1:
        confidence += 5

    return max(50, min(confidence, 100))


def _fallback_fraud_score(policy, memory):
    score = 5

    if policy["risk_level"] == "HIGH":
        score += 40
    elif policy["risk_level"] == "MEDIUM":
        score += 20

    memory_level = memory.get("risk_level", "LOW")

    if memory_level == "HIGH":
        score += 20
    elif memory_level == "MEDIUM":
        score += 10

    if memory.get("duplicate_invoice", False):
        score += 25

    if "Invoice total mismatch" in policy["reason"]:
        score += 30

    if any("Weekend" in flag for flag in policy.get("flags", [])):
        score += 5

    if memory.get("total_claims", 0) <= 1 and policy["risk_level"] == "LOW":
        score = 5

    return min(score, 100)


def _normalize_confidence(confidence):
    """
    Guard against the LLM returning a 0-1 probability instead of 0-100.
    decision_engine() compares confidence >= 80 (0-100 scale), so a decimal
    like 0.92 would make REJECT silently unreachable forever.
    """
    if 0 < confidence <= 1.0:
        confidence = confidence * 100
    return max(0, min(confidence, 100))


def _format_amount(value):
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def analyze_claim(title, amount, employee_id, invoice_amount=None, claim_date=None):
    print("=" * 50)
    print("Entered Amount :", amount)
    print("Invoice Amount :", invoice_amount)
    print("=" * 50)

    memory = get_employee_memory(employee_id)

    policy = check_policy(
        employee_id=employee_id,
        title=title,
        amount=amount,
        invoice_amount=invoice_amount,
        claim_date=claim_date,
        employee_history=memory
    )

    first_claim_note = "This is the employee's first claim, so do not use average amount as a fraud indicator."
    if not memory.get("is_first_claim"):
        first_claim_note = "This is not the first claim, so historical patterns may be considered."

    prompt = f"""
You are an Enterprise Expense Fraud Detection AI.

CURRENT CLAIM
-------------
Title: {title}
Amount: {_format_amount(amount)}
Invoice Amount: {_format_amount(invoice_amount)}

EMPLOYEE HISTORY
----------------
Total Claims: {memory['total_claims']}
Average Claim Amount: {_format_amount(memory.get('avg_amount', 0))}
High Value Claims: {memory['high_value_count']}
First Claim: {memory.get('is_first_claim', False)}

POLICY CHECK
------------
Violation: {policy['violation']}
Risk Level: {policy['risk_level']}
Reason: {policy['reason']}

IMPORTANT RULES
---------------
- Do NOT treat average amount as suspicious when total claims are 0 or 1.
- Normal meal or travel claims are not fraud by themselves.
- High average claim amount alone is NOT fraud.
- Focus only on duplicate receipts, invoice mismatch, old invoices, repeated suspicious behaviour, or abnormal claiming patterns.
- If this is the first claim, keep confidence high unless there is an actual policy violation.
- Do NOT infer fraud from lack of history alone.

{first_claim_note}

Return EXACTLY this format with whole numbers only (NOT decimals like 0.85):

Confidence: <a whole number from 0 to 100>

Fraud Score: <a whole number from 0 to 100>

Reasoning: <short explanation>
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )

        ai_text = response.choices[0].message.content

        fraud_score = extract_number(ai_text, "Fraud Score")
        confidence = extract_number(ai_text, "Confidence")

        # FIX: normalize confidence to 0-100 scale in case model drifts to 0-1
        confidence = _normalize_confidence(confidence)

        reasoning = extract_reasoning(ai_text)

        if fraud_score == 0 and confidence == 0:
            fraud_score = _fallback_fraud_score(policy, memory)
            confidence = _fallback_confidence(policy, memory)
            if not reasoning or reasoning == "No reasoning provided.":
                reasoning = policy["reason"] if policy["reason"] != "No violations detected" else "Normal claim pattern with no suspicious indicators."

        if confidence == 0:
            confidence = _fallback_confidence(policy, memory)

        if fraud_score == 0 and policy["risk_level"] == "LOW":
            fraud_score = 5

        # Any policy violation becomes REJECT; amount mismatch is ignored.
        if policy["violation"]:
            final_decision = "REJECT"
        else:
            final_decision = decision_engine(fraud_score, confidence)

        return {
            "ai_response": ai_text,
            "fraud_score": fraud_score,
            "confidence": confidence,
            "confidence_percent": f"{confidence}%",
            "reasoning": reasoning,
            "final_decision": final_decision,
            "policy": policy
        }

    except Exception as e:
        fallback_confidence = _fallback_confidence(policy, memory)
        fallback_fraud_score = _fallback_fraud_score(policy, memory)

        fallback_reasoning = policy["reason"] if policy["reason"] != "No violations detected" else "Normal claim pattern with no suspicious indicators."

        if policy["violation"]:
            fallback_decision = "REJECT"
        else:
            fallback_decision = "APPROVE" if policy["risk_level"] == "LOW" else "MANUAL_REVIEW"

        return {
            "ai_response": str(e),
            "fraud_score": fallback_fraud_score,
            "confidence": fallback_confidence,
            "confidence_percent": f"{fallback_confidence}%",
            "reasoning": fallback_reasoning,
            "final_decision": fallback_decision,
            "policy": policy
        }


def extract_number(text, field):
    try:
        pattern = rf"{re.escape(field)}\s*:\s*([\d.]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0
    except Exception:
        return 0


def extract_reasoning(text):
    try:
        match = re.search(r"Reasoning\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No reasoning provided."
    except Exception:
        return "No reasoning provided."
