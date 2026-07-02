def decision_engine(fraud_score, confidence):
    if fraud_score >= 90 and confidence >= 80:
        return "REJECT"
    elif fraud_score >= 50:
        return "MANUAL_REVIEW"
    else:
        return "APPROVE"