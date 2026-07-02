# ai_agents/agents/compliance_agent.py

from ai_agents.policy_engine import policy_engine

def compliance_agent(claim):
    """
    Strict company policy enforcement
    """

    result = policy_engine(claim)

    return {
        "violation": result["violation"],
        "reason": result["reason"],
        "action": result["action"]
    }