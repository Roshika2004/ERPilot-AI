from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ai_agents.policy_engine import policy_engine
from ai_agents.claim_analyzer import analyze_claim
from ai_agents.memory import get_employee_memory
from users.decorators import can_submit_claim

from .forms import ClaimForm


@login_required
@can_submit_claim
def create_claim(request):

    if request.method == "POST":

        form = ClaimForm(request.POST, request.FILES)

        if form.is_valid():

            claim = form.save(commit=False)
            claim.employee = request.user
            claim.save()

            employee_memory = get_employee_memory(request.user.id)

            # POLICY ENGINE
            policy_result = policy_engine(claim, employee_memory)

            if policy_result["violation"]:

                # Use policy_engine's actual decision — it already knows
                # APPROVE / MANUAL_REVIEW / REJECT based on the three-tier limits
                policy_decision = policy_result["decision"]

                claim.ai_recommendation = policy_decision
                claim.ai_reasoning = policy_result["reason"]

                if policy_decision == "REJECT":
                    claim.fraud_score = 100
                    claim.ai_confidence = 40
                    claim.status = "REJECTED"
                elif policy_decision == "MANUAL_REVIEW":
                    claim.fraud_score = 50
                    claim.ai_confidence = 60
                    claim.status = "PENDING"
                else:
                    # APPROVE — violation flagged but decision is still approve
                    claim.fraud_score = 10
                    claim.ai_confidence = 90
                    claim.status = "APPROVED"

                claim.save()

                messages.warning(
                    request,
                    f"Policy Triggered: {policy_result['reason']}"
                )

                return redirect("create_claim")

            # AI ANALYSIS
            try:

                ai_result = analyze_claim(
                    claim.title,
                    claim.amount,
                    request.user.id
                )

            except Exception as e:

                ai_result = {
                    "ai_response": f"AI ERROR: {str(e)}",
                    "confidence": 0,
                    "fraud_score": 0,
                    "reasoning": str(e),
                    "final_decision": "MANUAL_REVIEW"
                }

            # SAVE AI RESULTS
            claim.ai_recommendation = ai_result.get("final_decision", "MANUAL_REVIEW")
            claim.ai_confidence = ai_result.get("confidence", 0)
            claim.fraud_score = ai_result.get("fraud_score", 0)
            claim.ai_reasoning = ai_result.get("reasoning", "No reasoning provided")

            final_decision = ai_result.get("final_decision", "MANUAL_REVIEW")

            # STATUS MAPPING
            if final_decision == "APPROVE":
                claim.status = "APPROVED"
            elif final_decision == "REJECT":
                claim.status = "REJECTED"
            else:
                claim.status = "PENDING"

            claim.save()

            messages.success(
                request,
                "Claim submitted and analyzed successfully!"
            )

            return redirect("create_claim")

    else:

        form = ClaimForm()

    return render(
        request,
        "claims/create_claim.html",
        {"form": form}
    )
