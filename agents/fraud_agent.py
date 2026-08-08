"""agents/fraud_agent.py"""
import pandas as pd


class FraudAgent:
    """Combines Isolation Forest ML with deterministic risk heuristic rules."""

    def __init__(self, iso_forest, anomaly_columns: list):
        self.model = iso_forest
        self.anomaly_columns = anomaly_columns

    def evaluate_fraud_risk(self, input_df: pd.DataFrame) -> dict:
        # 1. ML Isolation Forest Anomaly
        anomaly_input = input_df[self.anomaly_columns]
        pred = self.model.predict(anomaly_input)[0]
        anomaly_score = float(self.model.decision_function(anomaly_input)[0])

        # 2. Heuristic Fraud Flags
        row = input_df.iloc[0]
        flags = []

        if row.get("device_change_frequency", 0) > 3:
            flags.append("HIGH_DEVICE_TURNOVER")
        if row.get("ecommerce_return_rate", 0.0) > 0.6:
            flags.append("SUSPICIOUS_ECOM_RETURN_PATTERN")
        if row.get("digital_footprint_consistency", 1.0) < 0.4:
            flags.append("INCONSISTENT_IDENTITY_FOOTPRINT")

        # IMPORTANT: cast every numpy scalar to a native Python type before
        # it goes anywhere near the FastAPI response — numpy.bool_/numpy.int64
        # are not JSON-serializable and jsonable_encoder will 500 on them.
        is_anomalous = bool((pred == -1) or (len(flags) >= 2))

        return {
            "is_anomalous": is_anomalous,
            "ml_anomaly_score": round(anomaly_score, 4),
            "fraud_risk_level": "CRITICAL" if len(flags) >= 2 else ("ELEVATED" if is_anomalous else "LOW"),
            "triggered_flags": flags
        }