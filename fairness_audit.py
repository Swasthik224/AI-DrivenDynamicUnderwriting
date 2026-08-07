"""
fairness_audit.py
-----------------
Audits the underwriting model for algorithmic bias and disparate impact
across demographic subgroups under the 80% rule standard.
"""

import joblib
import pandas as pd
import numpy as np


def run_fairness_audit():
    artifacts = joblib.load("underwriting_artifacts.pkl")
    model = artifacts["model"]
    feature_names = artifacts["feature_names"]

    df = pd.read_csv("underwriting_dataset.csv")
    df_consented = df[df["consent_given"] == True].copy()

    # Model Predictions (1 = Default/Reject, 0 = Non-Default/Approve)
    probs = model.predict_proba(df_consented[feature_names])[:, 1]
    # Approval decision: prob of default < 0.45
    df_consented["approved"] = (probs < 0.45).astype(int)

    results = {}

    # Audit Function
    def calculate_dir(dataframe, attribute, privileged_group):
        group_rates = dataframe.groupby(attribute)["approved"].mean()
        priv_rate = group_rates[privileged_group]

        dir_scores = {}
        for group, rate in group_rates.items():
            dir_val = rate / priv_rate if priv_rate > 0 else 0.0
            compliant = dir_val >= 0.80
            dir_scores[group] = {
                "approval_rate": round(float(rate), 4),
                "disparate_impact_ratio": round(float(dir_val), 4),
                "is_80_percent_compliant": bool(compliant)
            }
        return dir_scores

    results["gender_audit"] = calculate_dir(df_consented, "gender", privileged_group="Male")
    results["age_audit"] = calculate_dir(df_consented, "age_group", privileged_group="25_50")

    print("=" * 60)
    print("FAIRNESS & DISPARATE IMPACT AUDIT REPORT")
    print("=" * 60)

    print("\n[Gender Subgroup Analysis - Reference: Male]")
    for g, metrics in results["gender_audit"].items():
        status = "PASSED" if metrics["is_80_percent_compliant"] else "FAILED"
        print(
            f"  - {g:12s} | Approval Rate: {metrics['approval_rate']:.2%} | DIR: {metrics['disparate_impact_ratio']:.3f} | [{status}]")

    print("\n[Age Group Subgroup Analysis - Reference: 25_50]")
    for a, metrics in results["age_audit"].items():
        status = "PASSED" if metrics["is_80_percent_compliant"] else "FAILED"
        print(
            f"  - {a:12s} | Approval Rate: {metrics['approval_rate']:.2%} | DIR: {metrics['disparate_impact_ratio']:.3f} | [{status}]")

    return results


if __name__ == "__main__":
    run_fairness_audit()