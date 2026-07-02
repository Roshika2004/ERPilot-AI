# ai_agents/orchestrator/pipeline.py

from ai_agents.memory import get_employee_memory
from ai_agents.claim_analyzer import analyze_claim

from ai_agents.agents.fraud_agent import fraud_agent
from ai_agents.agents.finance_agent import finance_agent
from ai_agents.agents.compliance_agent import compliance_agent

from ai_agents.decision_engine import decision_engine


def run_multi_agent_pipeline(claim):

    employee_id = claim.employee.id

    # 1. MEMORY
    memory = get_employee_memory(employee_id)

    # 2. AI BASE ANALYSIS
    ai_result = analyze_claim(
        claim.title,
        claim.amount,
        employee_id
    )

    # 3. AGENTS RUN IN PARALLEL LOGIC (sequential here)

    fraud = fraud_agent(claim, memory, ai_result)
    finance = finance_agent(claim, memory)
    compliance = compliance_agent(claim)

    # 4. COMBINE SCORES
    final_fraud_score = (
        fraud["fraud_score"] * 0.5 +
        finance["finance_score"] * 0.3 +
        (100 if compliance["violation"] else 0) * 0.2
    )

    # 5. FINAL DECISION
    decision = decision_engine(
        fraud_score=final_fraud_score,
        confidence=ai_result["confidence"],
        policy_violation=compliance["violation"]
    )

    return {
        "ai_result": ai_result,
        "fraud": fraud,
        "finance": finance,
        "compliance": compliance,
        "final_fraud_score": final_fraud_score,
        "final_decision": decision
    }