"""agents/decision_agent.py"""


class DecisionAgent:
    """Applies underwriting policy guidelines based on Risk, Fraud, and DPDP status."""

    def render_decision(self, risk_score: float, fraud_res: dict, consent_verified: bool) -> dict:
        if not consent_verified:
            return {"decision": "REJECTED_NON_COMPLIANT", "reason": "Consent missing"}

        if fraud_res["is_anomalous"] or fraud_res["fraud_risk_level"] == "CRITICAL":
            return {
                "decision": "FLAGGED_FOR_MANUAL_REVIEW",
                "reason": f"Fraud flags triggered: {', '.join(fraud_res['triggered_flags'] or ['ML Anomaly'])}"
            }

        if risk_score >= 60.0:
            return {"decision": "APPROVED", "reason": "Low default risk meeting auto-approval thresholds."}
        elif risk_score >= 45.0:
            return {"decision": "CONDITIONAL_APPROVAL", "reason": "Moderate risk; lower credit line recommended."}
        else:
            return {"decision": "DECLINED", "reason": "Risk score below minimum threshold."}