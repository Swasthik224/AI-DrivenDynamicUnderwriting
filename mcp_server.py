import os
import json

import numpy as np
import pandas as pd
import uvicorn
from scipy import sparse
from mcp.server.fastmcp import FastMCP

import config
from agents import (
    ConsentAgent,
    AltDataAgent,
    FraudAgent,
    RiskPredictionAgent,
    XAIAgent,
    FairnessAgent,
    DecisionAgent,
    ReviewAgent,
)
from decision_log import log_decision, get_history
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
HOME_CREDIT_TEST_PATH = config.HOME_CREDIT_TEST_PATH

ARTIFACTS = None
_HOME_CREDIT_DF = None

consent_agent = ConsentAgent()
alt_agent = AltDataAgent()
decision_agent = DecisionAgent()
review_agent = ReviewAgent()

fraud_agent = None
risk_agent = None
xai_agent = None
fairness_agent = None


def load_artifacts():
    global ARTIFACTS
    global fraud_agent
    global risk_agent
    global xai_agent
    global fairness_agent

    ARTIFACTS = load_verified_artifacts(ARTIFACT_PATH)

    fraud_agent = FraudAgent(
        ARTIFACTS["isolation_forest"],
        ARTIFACTS["anomaly_columns"]
    )

    risk_agent = RiskPredictionAgent(
        ARTIFACTS["model"],
        ARTIFACTS["feature_names"]
    )

    xai_feature_names = ARTIFACTS.get("transformed_feature_names")

    if not xai_feature_names:
        preprocessor = ARTIFACTS["model"].named_steps["preprocessor"]
        xai_feature_names = preprocessor.get_feature_names_out().tolist()

    xai_agent = XAIAgent(
        ARTIFACTS["explainer"],
        list(xai_feature_names)
    )

    fairness_agent = FairnessAgent(
        ARTIFACTS["model"],
        ARTIFACTS["feature_names"]
    )


load_artifacts()


def get_home_credit_df() -> pd.DataFrame:
    global _HOME_CREDIT_DF

    if _HOME_CREDIT_DF is not None:
        return _HOME_CREDIT_DF

    if not os.path.exists(HOME_CREDIT_TEST_PATH):
        raise FileNotFoundError(
            f"Home Credit application_test.csv not found at: {HOME_CREDIT_TEST_PATH}"
        )

    df = pd.read_csv(HOME_CREDIT_TEST_PATH)

    if "SK_ID_CURR" not in df.columns:
        raise ValueError("SK_ID_CURR column is missing in application_test.csv.")

    df["SK_ID_CURR"] = df["SK_ID_CURR"].astype(str).str.strip()
    _HOME_CREDIT_DF = df
    return _HOME_CREDIT_DF


def to_python(value):
    if isinstance(value, dict):
        return {
            str(key): to_python(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_python(item) for item in value]

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, np.generic):
        return value.item()

    if pd.isna(value):
        return None

    return value


def prepare_feature_df(data: dict) -> pd.DataFrame:
    clean_data = data.copy()

    if clean_data.get("DAYS_EMPLOYED") == 365243:
        clean_data["DAYS_EMPLOYED"] = np.nan

    for feature in ARTIFACTS["feature_names"]:
        if feature not in clean_data:
            clean_data[feature] = np.nan

    return pd.DataFrame([clean_data])[ARTIFACTS["feature_names"]]


def prepare_shap_df(input_df: pd.DataFrame) -> pd.DataFrame:
    model = ARTIFACTS["model"]

    if not hasattr(model, "named_steps"):
        raise RuntimeError("The trained model pipeline does not expose preprocessing steps.")

    preprocessor = model.named_steps.get("preprocessor")

    if preprocessor is None:
        raise RuntimeError("Model preprocessor was not found.")

    transformed = preprocessor.transform(input_df)

    if sparse.issparse(transformed):
        transformed = transformed.toarray()

    feature_names = ARTIFACTS.get("transformed_feature_names")

    if not feature_names:
        feature_names = preprocessor.get_feature_names_out().tolist()

    if transformed.shape[1] != len(feature_names):
        raise ValueError("Transformed SHAP features do not match the artifact feature names.")

    return pd.DataFrame(
        transformed,
        columns=feature_names
    )


def normalize_sk_id(applicant_id: str) -> str:
    raw = str(applicant_id).strip()
    for prefix in ("SK_", "APP_", "sk_", "app_"):
        if raw.startswith(prefix):
            return raw[len(prefix):].strip()
    return raw


def load_applicant(applicant_id: str):
    df = get_home_credit_df()
    clean_id = normalize_sk_id(applicant_id)

    rows = df[df["SK_ID_CURR"] == clean_id]

    if rows.empty:
        return None

    record = rows.iloc[0].to_dict()

    if record.get("DAYS_EMPLOYED") == 365243:
        record["DAYS_EMPLOYED"] = np.nan

    record["applicant_id"] = str(applicant_id)
    record.setdefault("consent_given", True)

    return record


def consent_is_true(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if value is None or pd.isna(value):
        return False

    return str(value).strip().lower() in {
        "true", "1", "yes"
    }


def fetch_consented_applicant(applicant_id: str):
    if not valid_applicant_id(applicant_id):
        return None, {
            "success": False,
            "message": "Invalid applicant identifier."
        }

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return None, {
            "success": False,
            "message": f"Applicant '{applicant_id}' not found in Home Credit application_test.csv."
        }

    consent = consent_is_true(
        applicant.get("consent_given", False)
    )

    if not consent:
        return None, {
            "success": False,
            "message": "Applicant consent is required."
        }

    return applicant, None


@mcp.tool()
def get_applicant_data(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)

    if error:
        return error

    permitted = strip_protected(applicant)

    return {
        "success": True,
        "applicant": to_python(permitted)
    }


@mcp.tool()
def get_alternative_data(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)

    if error:
        return error

    try:
        result = alt_agent.process_signals(applicant)
    except Exception as exc:
        result = {
            "status": "NOT_AVAILABLE_IN_HOME_CREDIT",
            "note": str(exc)
        }

    return {
        "success": True,
        "applicant_id": applicant_id,
        "alternative_data": to_python(result)
    }


@mcp.tool()
def run_risk_prediction(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)

    if error:
        return error

    input_df = prepare_feature_df(applicant)
    result = risk_agent.predict_risk(input_df)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "risk_result": to_python(result)
    }


@mcp.tool()
def run_fraud_check(applicant_id: str) -> dict:
    applicant, error = fetch_consented_applicant(applicant_id)

    if error:
        return error

    input_df = prepare_feature_df(applicant)
    result = fraud_agent.evaluate_fraud_risk(input_df)

    return {
        "success": True,
        "applicant_id": applicant_id,
        "fraud_result": to_python(result)
    }


@mcp.tool()
def get_decision_history(applicant_id: str) -> dict:
    if not valid_applicant_id(applicant_id):
        return {
            "success": False,
            "message": "Invalid applicant identifier."
        }

    return {
        "success": True,
        "applicant_id": applicant_id,
        "history": to_python(get_history(applicant_id))
    }


@mcp.tool()
def run_fairness_audit() -> dict:
    try:
        df = get_home_credit_df()
        result = fairness_agent.audit_home_credit(df)

        return {
            "success": True,
            "fairness_audit": to_python(result)
        }

    except Exception as exc:
        return {
            "success": False,
            "message": "Fairness audit failed.",
            "error": str(exc)
        }


@mcp.tool()
def underwrite_applicant(applicant_id: str) -> dict:
    if not valid_applicant_id(applicant_id):
        return {
            "success": False,
            "message": "Invalid applicant identifier."
        }

    applicant = load_applicant(applicant_id)

    if applicant is None:
        return {
            "success": False,
            "message": f"Applicant '{applicant_id}' not found in Home Credit application_test.csv."
        }

    consent_result = consent_agent.verify_consent(
        consent_is_true(applicant.get("consent_given", False)),
        applicant_id
    )

    if not consent_result["verified"]:
        return {
            "success": True,
            "applicant_id": applicant_id,
            "decision": "REJECTED_NON_COMPLIANT",
            "decision_reason": consent_result["message"],
            "processing_stopped": True,
            "review_required": False,
            "decision_logged": False
        }

    model_features = ARTIFACTS["feature_names"]
    available_features = set(applicant.keys()) & set(model_features)

    if not available_features:
        return {
            "success": False,
            "applicant_id": applicant_id,
            "decision": "FLAGGED_FOR_MANUAL_REVIEW",
            "message": (
                "Applicant data does not contain any features expected by "
                "the currently loaded Home Credit model."
            ),
            "available_model_features": model_features,
            "applicant_features": list(applicant.keys()),
            "automatic_decision_blocked": True
        }

    input_df = prepare_feature_df(applicant)

    try:
        try:
            alternative_result = alt_agent.process_signals(applicant)
        except Exception as alt_exc:
            alternative_result = {
                "status": "NOT_AVAILABLE_IN_HOME_CREDIT",
                "note": str(alt_exc)
            }

        fraud_result = fraud_agent.evaluate_fraud_risk(
            input_df
        )

        risk_result = risk_agent.predict_risk(
            input_df
        )

        initial_decision = decision_agent.render_decision(
            risk_result["credit_risk_score"],
            fraud_result,
            consent_result["verified"]
        )

    except Exception as exc:
        return {
            "success": False,
            "applicant_id": applicant_id,
            "decision": "FLAGGED_FOR_MANUAL_REVIEW",
            "message": "Underwriting processing failed.",
            "error": str(exc),
            "automatic_decision_blocked": True
        }

    shap_drivers = []
    explanation_letter = ""
    xai_error = None

    try:
        shap_input = prepare_shap_df(input_df)

        shap_drivers = xai_agent.compute_shap_importance(
            shap_input
        )

        explanation_letter = xai_agent.generate_explanation_letter(
            initial_decision["decision"],
            risk_result["credit_risk_score"],
            shap_drivers
        )

        required_statement = (
            f"Decision: {initial_decision['decision']}. "
            f"Credit risk score: {risk_result['credit_risk_score']}/100."
        )

        if required_statement.lower() not in explanation_letter.lower():
            explanation_letter = (
                explanation_letter.rstrip()
                + "\n\n"
                + required_statement
            )

    except Exception as exc:
        xai_error = str(exc)

    if xai_error:
        review_result = {
            "self_check_passed": False,
            "issues": [
                "Explainability processing failed.",
                xai_error
            ],
            "note": "Automatic decision blocked because XAI could not complete."
        }

        final_decision = {
            "decision": "FLAGGED_FOR_MANUAL_REVIEW",
            "reason": "Explainability processing failed. Human review is required."
        }

    else:
        review_result = review_agent.review(
            initial_decision,
            risk_result,
            fraud_result,
            shap_drivers,
            explanation_letter
        )

        final_decision = initial_decision.copy()

        if not review_result["self_check_passed"]:
            final_decision = {
                "decision": "FLAGGED_FOR_MANUAL_REVIEW",
                "reason": (
                    "Automated review failed: "
                    + "; ".join(review_result["issues"])
                ),
                "previous_decision": initial_decision["decision"]
            }

    decision_name = final_decision["decision"]

    review_required = decision_name in {
        "FLAGGED_FOR_MANUAL_REVIEW",
        "CONDITIONAL_APPROVAL"
    }

    log_record = {
        "applicant_id": applicant_id,
        "decision": decision_name,
        "credit_risk_score": risk_result["credit_risk_score"],
        "risk_tier": risk_result["risk_tier"],
        "fraud_risk_level": fraud_result["fraud_risk_level"],
        "self_check_passed": review_result["self_check_passed"]
    }

    try:
        log_decision(log_record)
        decision_logged = True
    except Exception as exc:
        decision_logged = False
        logging_error = str(exc)

        final_decision = {
            "decision": "FLAGGED_FOR_MANUAL_REVIEW",
            "reason": "Decision logging failed. Human review is required.",
            "previous_decision": decision_name
        }

        review_required = True

    result = {
        "success": True,
        "applicant_id": applicant_id,
        "sk_id_curr": applicant.get("SK_ID_CURR"),
        "consent": consent_result,
        "alternative_data": to_python(alternative_result),
        "fraud_assessment": to_python(fraud_result),
        "risk_assessment": to_python(risk_result),
        "decision": final_decision["decision"],
        "decision_reason": final_decision["reason"],
        "review_required": review_required,
        "review_status": (
            "PENDING_MANUAL_REVIEW"
            if review_required
            else "AUTOMATED_CHECKS_PASSED"
        ),
        "xai": {
            "top_drivers": to_python(shap_drivers[:5]),
            "explanation_letter": explanation_letter,
            "error": xai_error
        },
        "self_check": to_python(review_result),
        "decision_logged": decision_logged
    }

    if not decision_logged:
        result["logging_error"] = logging_error

    if "previous_decision" in final_decision:
        result["previous_decision"] = final_decision["previous_decision"]

    result["decision_history"] = to_python(
        get_history(applicant_id)
    ) if decision_logged else []

    return result


@mcp.resource("underwriting://system")
def underwriting_system_info() -> str:
    return """
Enterprise Agentic Underwriting Pipeline (Home Credit Default Risk)

Agents:
1. Consent Agent
2. Alternative Data Agent
3. Fraud Agent
4. Risk Prediction Agent
5. XAI Agent
6. Decision Agent
7. Fairness Agent
8. Review Agent

MCP Tools:
1. get_applicant_data
2. get_alternative_data
3. run_risk_prediction
4. run_fraud_check
5. get_decision_history
6. run_fairness_audit
7. underwrite_applicant

ML Models:
- XGBoost
- Isolation Forest
- SHAP
"""


ALLOWED_HOSTS = {
    f"{config.MCP_HOST}:{config.MCP_PORT}".lower(),
    f"localhost:{config.MCP_PORT}".lower(),
    f"127.0.0.1:{config.MCP_PORT}".lower(),
}


class GuardMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower():
            value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        host = headers.get("host", "").strip().lower()
        authorization = headers.get("authorization", "")

        host_ok = host in ALLOWED_HOSTS

        token_ok = False

        if authorization.startswith("Bearer "):
            received_token = authorization[len("Bearer "):]

            token_ok = constant_time_equal(
                received_token,
                MCP_TOKEN
            )

        if host_ok and token_ok:
            await self.app(scope, receive, send)
            return

        status_code = 403 if not host_ok else 401

        body = json.dumps({
            "detail": "Unauthorized"
        }).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
        })


if __name__ == "__main__":
    uvicorn.run(
        GuardMiddleware(mcp.streamable_http_app()),
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level="info"
    )