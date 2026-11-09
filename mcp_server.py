import os

import pandas as pd
import uvicorn
from mcp.server.fastmcp import FastMCP

import config
from agents import (
    AltDataAgent,
    FraudAgent,
    RiskPredictionAgent,
    FairnessAgent,
)
from decision_log import get_history
from security import (
    constant_time_equal,
    load_verified_artifacts,
    strip_protected,
    valid_applicant_id,
)

MCP_TOKEN = config.secret("UW_MCP_TOKEN")
config.secret("UW_ARTIFACT_KEY")

mcp = FastMCP("Agentic Underwriting MCP Server")

ARTIFACT_PATH = config.ARTIFACT_PATH
DATASET_PATH = config.DATASET_PATH

ARTIFACTS = None
fraud_agent = None
risk_agent = None
alt_agent = AltDataAgent()
fairness_agent = None


def load_artifacts():
    global ARTIFACTS, fraud_agent, risk_agent, fairness_agent

    ARTIFACTS = load_verified_artifacts(ARTIFACT_PATH)

    fraud_agent = FraudAgent(ARTIFACTS["isolation_forest"], ARTIFACTS["anomaly_columns"])
    risk_agent = RiskPredictionAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])
    fairness_agent = FairnessAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])


load_artifacts()


def prepare_feature_df(data: dict) -> pd.DataFrame:
    clean_data = data.copy()
    for feature in ARTIFACTS["feature_names"]:
        if feature not in clean_data:
            clean_data[feature] = 0
    return pd.DataFrame([clean_data])[ARTIFACTS["feature_names"]]


def load_applicant(applicant_id: str):
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError("underwriting_dataset.csv not found.")
    df = pd.read_csv(DATASET_PATH)
    rows = df[df["applicant_id"].astype(str) == str(applicant_id)]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def fetch_consented_applicant(applicant_id: str):
    if not valid_applicant_id(applicant_id):
        return None, {"success": False, "message": "Invalid applicant identifier."}
    applicant = load_applicant(applicant_id)
    if applicant is None:
        return None, {"success": False, "message": "Applicant not found"}
    if not bool(applicant.get("consent_given", False)):
        return None, {"success": False, "message": "Applicant consent is required."}
    return applicant, None


@mcp.tool()
def get_applicant_data(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)
    if error:
        return error

    permitted = strip_protected(applicant)
    permitted = {
        key: value.item() if hasattr(value, "item") else value
        for key, value in permitted.items()
    }
    return {"success": True, "applicant": permitted}


@mcp.tool()
def get_alternative_data(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)
    if error:
        return error

    result = alt_agent.process_signals(applicant)
    return {"success": True, "applicant_id": applicant_id, "alternative_data": result}


@mcp.tool()
def run_risk_prediction(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)
    if error:
        return error

    input_df = prepare_feature_df(applicant)
    result = risk_agent.predict_risk(input_df)
    return {"success": True, "applicant_id": applicant_id, "risk_result": result}


@mcp.tool()
def run_fraud_check(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)
    if error:
        return error

    input_df = prepare_feature_df(applicant)
    result = fraud_agent.evaluate_fraud_risk(input_df)
    return {"success": True, "applicant_id": applicant_id, "fraud_result": result}


@mcp.tool()
def get_decision_history(applicant_id: str) -> dict:
    if not valid_applicant_id(applicant_id):
        return {"success": False, "message": "Invalid applicant identifier."}
    return {
        "success": True,
        "applicant_id": applicant_id,
        "history": get_history(applicant_id)
    }


@mcp.tool()
def run_fairness_audit() -> dict:
    if not os.path.exists(DATASET_PATH):
        return {"success": False, "message": "underwriting_dataset.csv not found."}
    df = pd.read_csv(DATASET_PATH)
    result = fairness_agent.audit(df)
    return {"success": True, "fairness_audit": result}


@mcp.resource("underwriting://system")
def underwriting_system_info() -> str:
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


ALLOWED_HOSTS = {
    f"{config.MCP_HOST}:{config.MCP_PORT}",
    f"localhost:{config.MCP_PORT}",
}


class GuardMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        host_ok = headers.get("host", "") in ALLOWED_HOSTS
        auth = headers.get("authorization", "")
        token_ok = auth.startswith("Bearer ") and constant_time_equal(auth[7:], MCP_TOKEN)

        if host_ok and token_ok:
            await self.app(scope, receive, send)
            return

        status = 403 if not host_ok else 401
        body = b'{"detail":"Unauthorized"}'
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


if __name__ == "__main__":
    uvicorn.run(
        GuardMiddleware(mcp.streamable_http_app()),
        host=config.MCP_HOST,
        port=config.MCP_PORT,
    )
