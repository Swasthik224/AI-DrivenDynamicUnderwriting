"""
train_model.py
--------------
Trains the XGBoost Credit Scoring Model, Isolation Forest Fraud Detector,
and exports SHAP explainer artifacts.
"""

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

FEATURE_COLUMNS = [
    "traditional_score",
    "monthly_income_inr",
    "debt_to_income_ratio",
    "num_existing_loans",
    "utility_pay_punctuality",
    "ecommerce_monthly_spend",
    "mobile_wallet_tx_freq",
    "gig_income_stability_index",
    "digital_footprint_consistency"
]

ANOMALY_COLUMNS = [
    "digital_footprint_consistency",
    "mobile_wallet_tx_freq",
    "ecommerce_monthly_spend"
]

def train_and_save():
    df = pd.read_csv("underwriting_dataset.csv")

    # Filter out records without explicit consent for model training
    df_consented = df[df["consent_given"] == True].copy()

    X = df_consented[FEATURE_COLUMNS]
    y = df_consented["default_flag"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # 1. Feature Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 2. XGBoost Credit Risk Model
    xgb_model = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )
    xgb_model.fit(X_train, y_train)

    # Model Evaluation
    y_pred_proba = xgb_model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"XGBoost ROC-AUC Score: {auc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, (y_pred_proba > 0.45).astype(int)))

    # 3. Isolation Forest for Anomaly / Digital Fraud Detection
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    iso_forest.fit(X_train[ANOMALY_COLUMNS])

    # 4. SHAP Tree Explainer
    explainer = shap.TreeExplainer(xgb_model)

    # Persist Artifacts
    artifacts = {
        "model": xgb_model,
        "scaler": scaler,
        "isolation_forest": iso_forest,
        "explainer": explainer,
        "feature_names": FEATURE_COLUMNS,
        "anomaly_columns": ANOMALY_COLUMNS
    }

    joblib.dump(artifacts, "underwriting_artifacts.pkl")
    print("All model artifacts successfully saved to 'underwriting_artifacts.pkl'.")

if __name__ == "__main__":
    train_and_save()