"""
mcp_server.py
-------------
MCP Server for Enterprise Agentic Underwriting Pipeline.

Provides controlled tools for:
- Applicant data
- Alternative-data metrics
- Fraud assessment
- Risk prediction
- Decision history
- Fairness audit
"""

import os
import joblib
import pandas as pd

from mcp.server.fastmcp import FastMCP

from agents import (
    AltDataAgent,
    FraudAgent,
    RiskPredictionAgent,
    FairnessAgent,
)

from decision_log import get_history


# ---------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------

mcp = FastMCP("Agentic Underwriting MCP Server")


# ---------------------------------------------------------
# LOAD ARTIFACTS
# ---------------------------------------------------------

ARTIFACT_PATH = "underwriting_artifacts.pkl"
DATASET_PATH = "underwriting_dataset.csv"

ARTIFACTS = None
fraud_agent = None
risk_agent = None
alt_agent = AltDataAgent()
fairness_agent = None


def load_artifacts():
    global ARTIFACTS
    global fraud_agent
    global risk_agent
    global fairness_agent

    if not os.path.exists(ARTIFACT_PATH):
        raise FileNotFoundError(
            "underwriting_artifacts.pkl not found. "
            "Run train_model.py first."
        )

    ARTIFACTS = joblib.load(ARTIFACT_PATH)

    fraud_agent = FraudAgent(
        ARTIFACTS["isolation_forest"],
        ARTIFACTS["anomaly_columns"]
    )

    risk_agent = RiskPredictionAgent(
        ARTIFACTS["model"],
        ARTIFACTS["feature_names"]
    )

    fairness_agent = FairnessAgent(
        ARTIFACTS["model"],
        ARTIFACTS["feature_names"]
    )


load_artifacts()


# ---------------------------------------------------------
# HELPER
# ---------------------------------------------------------

def prepare_feature_df(data: dict) -> pd.DataFrame:

    clean_data = data.copy()

    for feature in ARTIFACTS["feature_names"]:
        if feature not in clean_data:
            clean_data[feature] = 0

    return pd.DataFrame(
        [clean_data]
    )[ARTIFACTS["feature_names"]]


def load_applicant(applicant_id: str):

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            "underwriting_dataset.csv not found."
        )

    df = pd.read_csv(DATASET_PATH)

    rows = df[
        df["applicant_id"].astype(str) == str(applicant_id)
    ]

    if rows.empty:
        return None

    return rows.iloc[0].to_dict()


# =========================================================
# MCP TOOL 1
# =========================================================

@mcp.tool()
def get_applicant_data(applicant_id: str) -> dict:
    """
    Retrieve applicant underwriting data.

    Used by underwriting agents to obtain
    permitted applicant signals.
    """

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return {
            "success": False,
            "message": "Applicant not found"
        }

    # Convert numpy values into normal Python values
    applicant = {
        key: value.item() if hasattr(value, "item") else value
        for key, value in applicant.items()
    }

    return {
        "success": True,
        "applicant": applicant
    }


# =========================================================
# MCP TOOL 2
# =========================================================

@mcp.tool()
def get_alternative_data(applicant_id: str) -> dict:
    """
    Retrieve and aggregate alternative financial
    and behavioral signals for an applicant.
    """

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return {
            "success": False,
            "message": "Applicant not found"
        }

    if not bool(applicant.get("consent_given", False)):
        return {
            "success": False,
            "message": "Applicant consent is required."
        }

    result = alt_agent.process_signals(applicant)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "alternative_data": result
    }


# =========================================================
# MCP TOOL 3
# =========================================================

@mcp.tool()
def run_risk_prediction(applicant_id: str) -> dict:
    """
    Run the XGBoost credit-risk model for an applicant.
    """

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return {
            "success": False,
            "message": "Applicant not found"
        }

    if not bool(applicant.get("consent_given", False)):
        return {
            "success": False,
            "message": "Applicant consent is required."
        }

    input_df = prepare_feature_df(applicant)

    result = risk_agent.predict_risk(input_df)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "risk_result": result
    }


# =========================================================
# MCP TOOL 4
# =========================================================

@mcp.tool()
def run_fraud_check(applicant_id: str) -> dict:
    """
    Run Isolation Forest and deterministic fraud
    checks for an applicant.
    """

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return {
            "success": False,
            "message": "Applicant not found"
        }

    if not bool(applicant.get("consent_given", False)):
        return {
            "success": False,
            "message": "Applicant consent is required."
        }

    input_df = prepare_feature_df(applicant)

    result = fraud_agent.evaluate_fraud_risk(input_df)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "fraud_result": result
    }


# =========================================================
# MCP TOOL 5
# =========================================================

@mcp.tool()
def get_decision_history(applicant_id: str) -> dict:
    """
    Retrieve previous underwriting decisions
    for an applicant.
    """

    history = get_history(applicant_id)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "history": history
    }


# =========================================================
# MCP TOOL 6
# =========================================================

@mcp.tool()
def run_fairness_audit() -> dict:
    """
    Run gender and age-group fairness analysis
    using the current underwriting model.
    """

    if not os.path.exists(DATASET_PATH):
        return {
            "success": False,
            "message": "underwriting_dataset.csv not found."
        }

    df = pd.read_csv(DATASET_PATH)

    result = fairness_agent.audit(df)

    return {
        "success": True,
        "fairness_audit": result
    }


# =========================================================
# MCP RESOURCE
# =========================================================

@mcp.resource("underwriting://system")
def underwriting_system_info() -> str:
    """
    Information about the underwriting system.
    """

    return """
Enterprise Agentic Underwriting Pipeline

Agents:
1. Consent Agent
2. Alternative Data Agent
3. Fraud Agent
4. Risk Prediction Agent
5. XAI Agent
6. Decision Agent
7. Fairness Agent
8. Review Agent

ML Models:
- XGBoost
- Isolation Forest
- SHAP

MCP provides controlled access to underwriting
data and services through standardized tools.
"""


# =========================================================
# START SERVER
# =========================================================

import uvicorn

if __name__ == "__main__":
    mcp_app = mcp.streamable_http_app()

    uvicorn.run(
        mcp_app,
        host="127.0.0.1",
        port=8001
    )