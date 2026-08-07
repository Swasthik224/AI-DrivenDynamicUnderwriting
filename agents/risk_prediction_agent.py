"""agents/risk_prediction_agent.py"""
import pandas as pd


class RiskPredictionAgent:
    """XGBoost-backed PD (Probability of Default) and Credit Risk Score engine."""

    def __init__(self, model, feature_names: list):
        self.model = model
        self.feature_names = feature_names

    def predict_risk(self, input_df: pd.DataFrame) -> dict:
        df_ordered = input_df[self.feature_names]
        pd_prob = float(self.model.predict_proba(df_ordered)[0, 1])
        risk_score = round((1.0 - pd_prob) * 100, 1)

        return {
            "default_probability": round(pd_prob, 4),
            "credit_risk_score": risk_score,
            "risk_tier": "TIER_1_EXCELLENT" if risk_score >= 75 else (
                "TIER_2_GOOD" if risk_score >= 60 else (
                    "TIER_3_MODERATE" if risk_score >= 45 else "TIER_4_HIGH_RISK"
                )
            )
        }