from typing import Dict, Any, List

PROTECTED_TERMS = {"gender", "age_group", "age", "religion", "caste", "ethnicity"}


class ReviewAgent:
    def review(
        self,
        decision: Dict[str, Any],
        risk_res: Dict[str, Any],
        fraud_res: Dict[str, Any],
        shap_drivers: List[Dict[str, Any]],
        explanation_letter: str,
    ) -> Dict[str, Any]:
        issues = []

        score = risk_res["credit_risk_score"]
        expected_tier_ok = (
            (decision["decision"] == "APPROVED" and score >= 60.0) or
            (decision["decision"] == "CONDITIONAL_APPROVAL" and 45.0 <= score < 60.0) or
            (decision["decision"] == "DECLINED" and score < 45.0) or
            decision["decision"] in ("FLAGGED_FOR_MANUAL_REVIEW", "REJECTED_NON_COMPLIANT")
        )
        if not expected_tier_ok:
            issues.append("Decision does not match the score-tier policy — possible logic drift.")

        if fraud_res.get("is_anomalous") and decision["decision"] == "APPROVED":
            issues.append("Fraud flag present but decision is APPROVED — policy violation.")

        flagged_features = [
            d["feature"] for d in shap_drivers
            if any(term in d["feature"].lower() for term in PROTECTED_TERMS)
        ]
        if flagged_features:
            issues.append(f"Protected-attribute-like feature(s) found in SHAP drivers: {flagged_features}")

        letter_lower = explanation_letter.lower()
        if decision["decision"].split("_")[0].lower() not in letter_lower and "declined" not in letter_lower and "approved" not in letter_lower:
            issues.append("Explanation letter does not clearly state the decision outcome.")
        if str(score) not in explanation_letter:
            issues.append("Explanation letter does not cite the numeric risk score.")

        passed = len(issues) == 0

        return {
            "self_check_passed": passed,
            "issues": issues,
            "note": "Automated pre-release review against business policy and explainability requirements."
        }
