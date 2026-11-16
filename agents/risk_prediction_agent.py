
import pandas as pd


class RiskPredictionAgent:

    def __init__(self, model, feature_names: list):
        self.model = model
        self.feature_names = feature_names

    def predict_risk(self, input_df: pd.DataFrame) -> dict:
        missing_columns = [
            column for column in self.feature_names
            if column not in input_df.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing prediction features: "
                + ", ".join(missing_columns)
            )

        df_ordered = input_df[self.feature_names].copy()

        probability = float(
            self.model.predict_proba(df_ordered)[0, 1]
        )

        risk_score = round((1.0 - probability) * 100, 1)

        risk_tier = (
            "TIER_1_EXCELLENT" if risk_score >= 75 else
            "TIER_2_GOOD" if risk_score >= 60 else
            "TIER_3_MODERATE" if risk_score >= 45 else
            "TIER_4_HIGH_RISK"
        )

        return {
            "default_probability": round(probability, 4),
            "credit_risk_score": risk_score,
            "risk_tier": risk_tier
        }
