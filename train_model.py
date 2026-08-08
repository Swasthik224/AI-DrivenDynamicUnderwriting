"""
train_model.py
--------------
Trains XGBoost credit model + Isolation Forest fraud detector + SHAP explainer,
using the exact feature set the API and dashboard send at inference time.
"""

import joblib
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# NOTE: gender/age_group are deliberately excluded from the model — they're
# protected attributes and are only used later by FairnessAgent for auditing.
FEATURE_COLUMNS = [
    "traditional_score",
    "monthly_income_inr",
    "debt_to_income_ratio",
    "num_existing_loans",
    "upi_monthly_tx_volume",
    "bnpl_repayment_rate",
    "utility_pay_punctuality",
    "telecom_recharge_regularity",
    "ecommerce_monthly_spend",
    "ecommerce_return_rate",
    "gig_income_stability_index",
    "digital_footprint_consistency",
    "device_change_frequency",
    "mobile_wallet_tx_freq",
]

# Signals most indicative of synthetic identity / fraud patterns
ANOMALY_COLUMNS = [
    "digital_footprint_consistency",
    "device_change_frequency",
    "ecommerce_return_rate",
]


def train_and_save():
    df = pd.read_csv("underwriting_dataset.csv")

    # Robust consent filtering (handles bool True/1 or string 'true'/'True')
    if "consent_given" in df.columns:
        if df["consent_given"].dtype == object:
            mask = df["consent_given"].astype(str).str.strip().str.lower().isin(["true", "1"])
        else:
            mask = df["consent_given"] == True
        df_consented = df[mask].copy()
    else:
        df_consented = df.copy()

    # Fallback to full dataset if consent filter leaves insufficient records
    if len(df_consented) < 5 or df_consented["default_flag"].nunique() < 2:
        print("⚠️ Warning: Consented subset too small or single-class. Using full dataset for training.")
        df_consented = df.copy()

    X = df_consented[FEATURE_COLUMNS]
    y = df_consented["default_flag"]

    # Check class distribution to safely apply stratification
    class_counts = y.value_counts()
    should_stratify = y if (len(class_counts) > 1 and class_counts.min() >= 2) else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=should_stratify
    )

    xgb_model = XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss"
    )
    xgb_model.fit(X_train, y_train)

    y_pred_proba = xgb_model.predict_proba(X_test)[:, 1]

    if len(y_test.unique()) > 1:
        print(f"XGBoost ROC-AUC: {roc_auc_score(y_test, y_pred_proba):.4f}")
        print(classification_report(y_test, (y_pred_proba > 0.45).astype(int), zero_division=0))
    else:
        print("XGBoost training complete.")

    iso_forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso_forest.fit(X_train[ANOMALY_COLUMNS])

    explainer = shap.TreeExplainer(xgb_model)

    artifacts = {
        "model": xgb_model,
        "isolation_forest": iso_forest,
        "explainer": explainer,
        "feature_names": FEATURE_COLUMNS,
        "anomaly_columns": ANOMALY_COLUMNS,
    }
    joblib.dump(artifacts, "underwriting_artifacts.pkl")
    print("✅ Artifacts saved successfully to 'underwriting_artifacts.pkl'.")


if __name__ == "__main__":
    train_and_save()