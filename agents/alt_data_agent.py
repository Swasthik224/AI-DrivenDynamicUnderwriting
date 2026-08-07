"""agents/alt_data_agent.py"""
import pandas as pd


class AltDataAgent:
    """Aggregates and transforms unstructured digital footprint signals."""

    def process_signals(self, raw_data: dict) -> dict:
        # Compute composite alternative score (0 - 100)
        upi_health = min(raw_data["upi_monthly_tx_volume"] / 50.0, 1.0) * 25
        bnpl_health = raw_data["bnpl_repayment_rate"] * 25
        telecom_health = raw_data["telecom_recharge_regularity"] * 25
        gig_health = raw_data["gig_income_stability_index"] * 25

        alt_composite_score = round(upi_health + bnpl_health + telecom_health + gig_health, 1)

        return {
            "alt_composite_score": alt_composite_score,
            "financial_footprint_index": round(
                (raw_data["bnpl_repayment_rate"] + raw_data["utility_pay_punctuality"]) / 2, 2),
            "digital_reliability_index": round(
                (raw_data["telecom_recharge_regularity"] + raw_data["digital_footprint_consistency"]) / 2, 2)
        }