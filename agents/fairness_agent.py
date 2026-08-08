"""agents/fairness_agent.py"""
import pandas as pd


class FairnessAgent:
    """Computes disparate-impact metrics using the ACTUAL decision policy
    (score >= 60 => auto-approved), not a raw probability cutoff."""

    def __init__(self, model, feature_names: list, threshold: float = 0.80, approval_score: float = 60.0):
        self.model = model
        self.feature_names = feature_names
        self.dir_threshold = threshold
        self.approval_score = approval_score

    def audit(self, df: pd.DataFrame) -> dict:
        consented_df = df[df["consent_given"] == True].copy()
        probs = self.model.predict_proba(consented_df[self.feature_names])[:, 1]
        risk_score = (1.0 - probs) * 100
        consented_df["approved"] = (risk_score >= self.approval_score).astype(int)

        def _get_group_metrics(protected_col: str, privileged_group: str):
            grouped = consented_df.groupby(protected_col)["approved"].mean()
            priv_rate = grouped.get(privileged_group, 1.0)

            metrics = {}
            for group, app_rate in grouped.items():
                dir_score = app_rate / priv_rate if priv_rate > 0 else 0.0
                metrics[str(group)] = {
                    "approval_rate": round(float(app_rate), 4),
                    "disparate_impact_ratio": round(float(dir_score), 4),
                    "demographic_parity_difference": round(float(abs(priv_rate - app_rate)), 4),
                    "passes_80_percent_rule": bool(dir_score >= self.dir_threshold)
                }
            return metrics

        return {
            "approval_definition": f"credit_risk_score >= {self.approval_score} (matches live DecisionAgent policy)",
            "gender_fairness": _get_group_metrics("gender", privileged_group="Male"),
            "age_fairness": _get_group_metrics("age_group", privileged_group="25_50")
        }