"""
app.py - Multi-Agent Event-Driven FastAPI Backend
"""
import os
import joblib
import pandas as pd
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from agents import (
    ConsentAgent, AltDataAgent, FraudAgent,
    RiskPredictionAgent, XAIAgent, FairnessAgent,
    DecisionAgent, ReviewAgent
)
from decision_log import log_decision, get_history

ARTIFACTS = None
consent_agent = ConsentAgent()
alt_agent = AltDataAgent()
decision_agent = DecisionAgent()
review_agent = ReviewAgent()

fraud_agent = None
risk_agent = None
xai_agent = None
fairness_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ARTIFACTS, fraud_agent, risk_agent, xai_agent, fairness_agent
    if os.path.exists("underwriting_artifacts.pkl"):
        ARTIFACTS = joblib.load("underwriting_artifacts.pkl")
        fraud_agent = FraudAgent(ARTIFACTS["isolation_forest"], ARTIFACTS["anomaly_columns"])
        risk_agent = RiskPredictionAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])
        xai_agent = XAIAgent(ARTIFACTS["explainer"], ARTIFACTS["feature_names"])
        fairness_agent = FairnessAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])
        print("✅ All Autonomous Agents Initialized Successfully.")
    else:
        raise FileNotFoundError("Run 'python train_model.py' first.")
    yield

app = FastAPI(title="Enterprise Agentic Underwriting Pipeline", lifespan=lifespan)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FullApplicantSchema(BaseModel):
    applicant_id: str = Field("APP_1042", json_schema_extra={"example": "APP_1042"})
    gender: str = Field("Female", json_schema_extra={"example": "Female"})
    age_group: str = Field("25_50", json_schema_extra={"example": "25_50"})
    consent_given: bool = Field(True, json_schema_extra={"example": True})
    traditional_score: float = Field(680.0, ge=300, le=850)
    monthly_income_inr: float = Field(85000.0, ge=0)
    debt_to_income_ratio: float = Field(0.28, ge=0.0, le=1.0)
    upi_monthly_tx_volume: int = Field(42, ge=0)
    bnpl_repayment_rate: float = Field(0.95, ge=0.0, le=1.0)
    utility_pay_punctuality: float = Field(0.90, ge=0.0, le=1.0)
    telecom_recharge_regularity: float = Field(0.88, ge=0.0, le=1.0)
    ecommerce_monthly_spend: float = Field(12000.0, ge=0)
    ecommerce_return_rate: float = Field(0.08, ge=0.0, le=1.0)
    gig_income_stability_index: float = Field(0.82, ge=0.0, le=1.0)
    digital_footprint_consistency: float = Field(0.91, ge=0.0, le=1.0)
    device_change_frequency: int = Field(1, ge=0)

    # Optional fields to allow dynamic features without validation failure
    num_existing_loans: Optional[int] = 0
    mobile_wallet_tx_freq: Optional[int] = 0

class BehavioralEventPayload(BaseModel):
    applicant_id: str
    event_type: str = Field(..., json_schema_extra={"example": "UTILITY_PAYMENT_MISSED"})
    metric_updated: str = Field(..., json_schema_extra={"example": "utility_pay_punctuality"})
    new_value: float = Field(..., ge=0.0, le=1.0)
    applicant_data: FullApplicantSchema

def prepare_feature_df(data_dict: dict) -> pd.DataFrame:
    """Safely aligns dictionary data with trained model feature expectations."""
    clean_dict = data_dict.copy()
    for feat in ARTIFACTS["feature_names"]:
        if feat not in clean_dict:
            clean_dict[feat] = 0
    return pd.DataFrame([clean_dict])[ARTIFACTS["feature_names"]]

@app.post("/api/v1/underwrite", status_code=200)
def underwrite(applicant: FullApplicantSchema):
    # Agent 1: Consent Verification
    c_res = consent_agent.verify_consent(applicant.consent_given, applicant.applicant_id)
    if not c_res["verified"]:
        raise HTTPException(status_code=403, detail=c_res["message"])

    raw_dict = applicant.model_dump()
    input_df = prepare_feature_df(raw_dict)

    # Debug logs safely executed inside request flow
    print("DEBUG feature_names:", ARTIFACTS["feature_names"])
    print("DEBUG input_df row:\n", input_df.iloc[0].to_dict())

    # Agent 2: Alt Data Aggregation
    alt_res = alt_agent.process_signals(raw_dict)

    # Agent 3: Fraud Evaluation
    fraud_res = fraud_agent.evaluate_fraud_risk(input_df)

    # Agent 4: Risk Prediction
    risk_res = risk_agent.predict_risk(input_df)

    # Agent 5: Decision Render
    decision_res = decision_agent.render_decision(
        risk_res["credit_risk_score"], fraud_res, applicant.consent_given
    )

    # Agent 6: Explainability (XAI)
    shap_drivers = xai_agent.compute_shap_importance(input_df)
    letter = xai_agent.generate_explanation_letter(
        decision_res["decision"], risk_res["credit_risk_score"], shap_drivers
    )

    # Agent 8: Self-check against business policy BEFORE returning
    review_res = review_agent.review(decision_res, risk_res, fraud_res, shap_drivers, letter)
    if not review_res["self_check_passed"]:
        # Fail safe: don't auto-approve something that failed policy review
        if decision_res["decision"] == "APPROVED":
            decision_res = {
                "decision": "FLAGGED_FOR_MANUAL_REVIEW",
                "reason": f"Self-check failed: {'; '.join(review_res['issues'])}"
            }

    # Audit Logging
    log_decision({
        "applicant_id": applicant.applicant_id,
        "decision": decision_res["decision"],
        "credit_risk_score": risk_res["credit_risk_score"],
        "risk_tier": risk_res["risk_tier"],
        "fraud_risk_level": fraud_res["fraud_risk_level"],
        "self_check_passed": review_res["self_check_passed"],
    })

    return {
        "applicant_id": applicant.applicant_id,
        "decision": decision_res["decision"],
        "decision_reason": decision_res["reason"],
        "credit_risk_score": risk_res["credit_risk_score"],
        "risk_tier": risk_res["risk_tier"],
        "default_probability": risk_res["default_probability"],
        "alt_data_metrics": alt_res,
        "fraud_assessment": fraud_res,
        "top_shap_drivers": shap_drivers[:4],
        "explanation_letter": letter,
        "self_check": review_res,
    }

@app.post("/api/v1/event-update", status_code=200)
def process_behavioral_event(event: BehavioralEventPayload):
    """Event-Driven API: Processes real-time updates and measures score delta."""
    base_data = event.applicant_data.model_dump()

    # Baseline Score
    df_base = prepare_feature_df(base_data)
    base_score = risk_agent.predict_risk(df_base)["credit_risk_score"]

    # Apply Event Update
    updated_data = base_data.copy()
    updated_data[event.metric_updated] = event.new_value
    df_updated = prepare_feature_df(updated_data)

    updated_risk = risk_agent.predict_risk(df_updated)
    score_delta = round(updated_risk["credit_risk_score"] - base_score, 1)

    return {
        "applicant_id": event.applicant_id,
        "event_processed": event.event_type,
        "original_score": base_score,
        "new_score": updated_risk["credit_risk_score"],
        "score_delta": score_delta,
        "new_decision": decision_agent.render_decision(
            updated_risk["credit_risk_score"], {"is_anomalous": False, "fraud_risk_level": "LOW"}, True
        )["decision"]
    }

@app.get("/api/v1/fairness-audit", status_code=200)
def audit_fairness():
    df = pd.read_csv("underwriting_dataset.csv")
    return fairness_agent.audit(df)

@app.get("/api/v1/decision-history/{applicant_id}", status_code=200)
def decision_history(applicant_id: str):
    """Returns logged decisions for an applicant — use this to show score
    drift over time in the live demo (call underwrite twice, then hit this)."""
    return {"applicant_id": applicant_id, "history": get_history(applicant_id)}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)