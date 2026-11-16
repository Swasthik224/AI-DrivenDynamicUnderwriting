import io
import os
import json
import time
import hmac
import base64
import hashlib
import subprocess
import sys
import httpx
import numpy as np
import pandas as pd
import uvicorn
from scipy import sparse
import config

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

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
from security import constant_time_equal, load_verified_artifacts, safe_text


ARTIFACTS = None
MCP_SERVER_URL = config.MCP_URL
MCP_TOKEN = config.secret("UW_MCP_TOKEN")
JWT_SECRET = config.secret("UW_ARTIFACT_KEY").encode("utf-8")

consent_agent = ConsentAgent()
alt_agent = AltDataAgent()
decision_agent = DecisionAgent()
review_agent = ReviewAgent()

fraud_agent = None
risk_agent = None
xai_agent = None
fairness_agent = None

# In-memory operational stores (backed by decision_log.py for tamper-evident audit trail)
REVIEW_QUEUE: dict[str, dict] = {}
AUDIT_HISTORY: list[dict] = []

USERS = {
    "officer": {
        "password": os.environ.get("UW_OFFICER_PASS", "officer123"),
        "role": "LOAN_OFFICER",
        "full_name": "Aarav Mehta (Loan Officer)",
    },
    "underwriter": {
        "password": os.environ.get("UW_UNDERWRITER_PASS", "underwriter123"),
        "role": "SENIOR_UNDERWRITER",
        "full_name": "Priya Nair (Senior Underwriter)",
    },
    "admin": {
        "password": os.environ.get("UW_ADMIN_PASS", "admin123"),
        "role": "RISK_ADMIN",
        "full_name": "Vikram Rao (Risk Admin)",
    },
}

ROLE_PERMISSIONS = {
    "LOAN_OFFICER": {"underwrite", "lookup", "batch", "view_history"},
    "SENIOR_UNDERWRITER": {"underwrite", "lookup", "batch", "view_history", "override_review"},
    "RISK_ADMIN": {"underwrite", "lookup", "batch", "view_history", "override_review", "fairness_audit", "retrain"},
}


# ---------------------------------------------------------------------------
# JWT Helpers (Zero external dependency HS256 using stdlib hmac + hashlib)
# ---------------------------------------------------------------------------
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt(username: str, role: str, full_name: str, ttl_seconds: int = 28800) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": username,
                "role": role,
                "name": full_name,
                "iat": int(time.time()),
                "exp": int(time.time()) + ttl_seconds,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = _b64url_encode(hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Malformed authentication token.")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _b64url_encode(hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(sig_b64, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature.")
    try:
        claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    if int(claims.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return claims


def require_permission(permission: str):
    def dependency(authorization: Optional[str] = Header(None)) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer authentication token.")
        token = authorization[len("Bearer "):].strip()
        claims = verify_jwt(token)
        role = claims.get("role", "")
        if permission not in ROLE_PERMISSIONS.get(role, set()):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' is not authorized for action '{permission}'.",
            )
        return claims

    return dependency


# ---------------------------------------------------------------------------
# Artifact Loading & MCP Client
# ---------------------------------------------------------------------------
def reload_model_artifacts():
    global ARTIFACTS, fraud_agent, risk_agent, xai_agent, fairness_agent

    if not os.path.exists(config.ARTIFACT_PATH):
        raise FileNotFoundError("Model artifacts not found. Run 'python train_model.py' first.")

    ARTIFACTS = load_verified_artifacts(config.ARTIFACT_PATH)

    fraud_agent = FraudAgent(ARTIFACTS["isolation_forest"], ARTIFACTS["anomaly_columns"])
    risk_agent = RiskPredictionAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])

    xai_feature_names = ARTIFACTS.get("transformed_feature_names")
    if not xai_feature_names:
        preprocessor = ARTIFACTS["model"].named_steps["preprocessor"]
        xai_feature_names = preprocessor.get_feature_names_out().tolist()

    xai_agent = XAIAgent(ARTIFACTS["explainer"], list(xai_feature_names))
    fairness_agent = FairnessAgent(ARTIFACTS["model"], ARTIFACTS["feature_names"])


def _mcp_headers() -> dict:
    return {"Authorization": f"Bearer {MCP_TOKEN}"}


async def call_mcp_tool(tool_name: str, arguments: dict):
    async with httpx.AsyncClient(headers=_mcp_headers(), timeout=30.0) as http_client:
        async with streamable_http_client(MCP_SERVER_URL, http_client=http_client) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)


def extract_mcp_result(result):
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return result.structured_content

    if hasattr(result, "content"):
        output = []
        for item in result.content:
            if hasattr(item, "text"):
                try:
                    output.append(json.loads(item.text))
                except Exception:
                    output.append(item.text)
            else:
                output.append(str(item))
        return output[0] if len(output) == 1 else output

    return str(result)


@asynccontextmanager
async def lifespan(app: FastAPI):
    reload_model_artifacts()
    print("All Autonomous Agents & RBAC Security Initialized Successfully.")
    yield


app = FastAPI(title="Enterprise Agentic Underwriting Workstation", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class OverrideRequest(BaseModel):
    override_decision: str = Field(..., pattern="^(APPROVED|DECLINED|CONDITIONAL_APPROVAL)$")
    reviewer_notes: str = Field(..., min_length=3, max_length=500)


class FullApplicantSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    applicant_id: str = Field("100001")
    consent_given: bool = Field(True)

    AMT_INCOME_TOTAL: Optional[float] = None
    AMT_CREDIT: Optional[float] = None
    AMT_ANNUITY: Optional[float] = None
    AMT_GOODS_PRICE: Optional[float] = None
    REGION_POPULATION_RELATIVE: Optional[float] = None
    DAYS_EMPLOYED: Optional[float] = None
    DAYS_REGISTRATION: Optional[float] = None
    DAYS_ID_PUBLISH: Optional[float] = None
    CNT_CHILDREN: Optional[float] = None
    CNT_FAM_MEMBERS: Optional[float] = None
    HOUR_APPR_PROCESS_START: Optional[float] = None
    FLAG_OWN_CAR: Optional[str] = None
    FLAG_OWN_REALTY: Optional[str] = None
    NAME_INCOME_TYPE: Optional[str] = None
    NAME_EDUCATION_TYPE: Optional[str] = None
    NAME_FAMILY_STATUS: Optional[str] = None
    NAME_HOUSING_TYPE: Optional[str] = None
    OCCUPATION_TYPE: Optional[str] = None
    WEEKDAY_APPR_PROCESS_START: Optional[str] = None
    ORGANIZATION_TYPE: Optional[str] = None


def prepare_feature_df(data_dict: dict) -> pd.DataFrame:
    clean_dict = data_dict.copy()
    if clean_dict.get("DAYS_EMPLOYED") == 365243:
        clean_dict["DAYS_EMPLOYED"] = np.nan

    for feat in ARTIFACTS["feature_names"]:
        if feat not in clean_dict or clean_dict[feat] is None:
            clean_dict[feat] = np.nan

    return pd.DataFrame([clean_dict])[ARTIFACTS["feature_names"]]


def prepare_shap_df(input_df: pd.DataFrame) -> pd.DataFrame:
    model = ARTIFACTS["model"]
    preprocessor = model.named_steps["preprocessor"]
    transformed = preprocessor.transform(input_df)
    if sparse.issparse(transformed):
        transformed = transformed.toarray()

    feature_names = ARTIFACTS.get("transformed_feature_names")
    if not feature_names:
        feature_names = preprocessor.get_feature_names_out().tolist()

    return pd.DataFrame(transformed, columns=feature_names)


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/login")
def login(creds: LoginRequest):
    user = USERS.get(creds.username.strip().lower())
    if not user or not constant_time_equal(creds.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_jwt(creds.username.strip().lower(), user["role"], user["full_name"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": creds.username.strip().lower(),
        "role": user["role"],
        "full_name": user["full_name"],
        "permissions": sorted(list(ROLE_PERMISSIONS[user["role"]])),
    }


@app.get("/api/v1/auth/me")
def whoami(claims: dict = Depends(require_permission("view_history"))):
    role = claims["role"]
    return {
        "username": claims["sub"],
        "role": role,
        "full_name": claims["name"],
        "permissions": sorted(list(ROLE_PERMISSIONS.get(role, set()))),
    }


# ---------------------------------------------------------------------------
# Tab 1: Underwrite & Live MCP Lookup
# ---------------------------------------------------------------------------
@app.get("/api/v1/mcp-status")
async def mcp_status(claims: dict = Depends(require_permission("lookup"))):
    try:
        async with httpx.AsyncClient(headers=_mcp_headers(), timeout=15.0) as http_client:
            async with streamable_http_client(MCP_SERVER_URL, http_client=http_client) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    return {
                        "mcp_connected": True,
                        "mcp_server": MCP_SERVER_URL,
                        "tools": [t.name for t in tools_result.tools],
                    }
    except Exception as e:
        return {"mcp_connected": False, "mcp_server": MCP_SERVER_URL, "error": str(e)}


@app.get("/api/v1/mcp-applicant/{applicant_id}")
async def mcp_applicant(applicant_id: str, claims: dict = Depends(require_permission("lookup"))):
    try:
        result = await call_mcp_tool("get_applicant_data", {"applicant_id": applicant_id})
        extracted = extract_mcp_result(result)
        return {"mcp_connected": True, "applicant_id": applicant_id, "result": extracted}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MCP lookup failed: {str(e)}")


@app.post("/api/v1/underwrite", status_code=200)
async def underwrite(
    applicant: FullApplicantSchema,
    claims: dict = Depends(require_permission("underwrite")),
):
    c_res = consent_agent.verify_consent(applicant.consent_given, applicant.applicant_id)
    if not c_res["verified"]:
        raise HTTPException(status_code=403, detail=c_res["message"])

    mcp_extracted = None
    mcp_status_flag = "NOT_CALLED"
    try:
        mcp_result = await call_mcp_tool("get_applicant_data", {"applicant_id": applicant.applicant_id})
        mcp_extracted = extract_mcp_result(mcp_result)
        mcp_status_flag = "SUCCESS"
    except Exception as e:
        mcp_status_flag = "FAILED"
        print("MCP lookup warning:", e)

    raw_dict = applicant.model_dump(exclude_none=True)
    if (
        isinstance(mcp_extracted, dict)
        and mcp_extracted.get("success")
        and isinstance(mcp_extracted.get("applicant"), dict)
    ):
        merged = mcp_extracted["applicant"].copy()
        merged.update(raw_dict)
        raw_dict = merged

    input_df = prepare_feature_df(raw_dict)

    try:
        alt_res = alt_agent.process_signals(raw_dict)
    except Exception as alt_exc:
        alt_res = {"status": "NOT_AVAILABLE_IN_HOME_CREDIT", "note": str(alt_exc)}

    fraud_res = fraud_agent.evaluate_fraud_risk(input_df)
    risk_res = risk_agent.predict_risk(input_df)
    decision_res = decision_agent.render_decision(
        risk_res["credit_risk_score"], fraud_res, applicant.consent_given
    )

    shap_input = prepare_shap_df(input_df)
    shap_drivers = xai_agent.compute_shap_importance(shap_input)
    letter = xai_agent.generate_explanation_letter(
        decision_res["decision"], risk_res["credit_risk_score"], shap_drivers
    )

    review_res = review_agent.review(decision_res, risk_res, fraud_res, shap_drivers, letter)

    if not review_res["self_check_passed"]:
        decision_res = {
            "decision": "FLAGGED_FOR_MANUAL_REVIEW",
            "reason": "Automated policy check flagged: " + "; ".join(review_res["issues"]),
            "previous_decision": decision_res["decision"],
        }

    record = {
        "applicant_id": applicant.applicant_id,
        "decision": decision_res["decision"],
        "credit_risk_score": risk_res["credit_risk_score"],
        "risk_tier": risk_res["risk_tier"],
        "fraud_risk_level": fraud_res["fraud_risk_level"],
        "self_check_passed": review_res["self_check_passed"],
    }
    log_decision(record)

    audit_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "applicant_id": applicant.applicant_id,
        "submitted_by": claims["sub"],
        "decision": decision_res["decision"],
        "decision_reason": decision_res["reason"],
        "credit_risk_score": risk_res["credit_risk_score"],
        "risk_tier": risk_res["risk_tier"],
        "default_probability": risk_res["default_probability"],
        "fraud_risk_level": fraud_res["fraud_risk_level"],
        "top_shap_drivers": shap_drivers[:4],
        "self_check": review_res,
        "override_by": None,
        "override_notes": None,
    }
    AUDIT_HISTORY.insert(0, audit_entry)

    if decision_res["decision"] in {"FLAGGED_FOR_MANUAL_REVIEW", "CONDITIONAL_APPROVAL"}:
        REVIEW_QUEUE[applicant.applicant_id] = audit_entry.copy()

    return {
        "applicant_id": applicant.applicant_id,
        "mcp": {"server": MCP_SERVER_URL, "status": mcp_status_flag, "result": mcp_extracted},
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


# ---------------------------------------------------------------------------
# Tab 2: Manual Review Queue & Senior Underwriter Override
# ---------------------------------------------------------------------------
@app.get("/api/v1/review-queue")
def get_review_queue(claims: dict = Depends(require_permission("view_history"))):
    return {"count": len(REVIEW_QUEUE), "items": list(REVIEW_QUEUE.values())}


@app.post("/api/v1/review-queue/{applicant_id}/override")
def override_application(
    applicant_id: str,
    body: OverrideRequest,
    claims: dict = Depends(require_permission("override_review")),
):
    item = REVIEW_QUEUE.get(applicant_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Applicant '{applicant_id}' is not in the manual review queue.")

    clean_notes = safe_text(body.reviewer_notes, 500)
    item["decision"] = body.override_decision
    item["decision_reason"] = f"Senior Underwriter Override ({claims['sub']}): {clean_notes}"
    item["override_by"] = claims["sub"]
    item["override_notes"] = clean_notes
    item["override_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    log_decision({
        "applicant_id": applicant_id,
        "decision": body.override_decision,
        "credit_risk_score": item["credit_risk_score"],
        "risk_tier": item["risk_tier"],
        "fraud_risk_level": item["fraud_risk_level"],
        "self_check_passed": True,
    })

    AUDIT_HISTORY.insert(0, item.copy())
    del REVIEW_QUEUE[applicant_id]

    return {"success": True, "updated_record": item}


# ---------------------------------------------------------------------------
# Tab 3: Vectorized Batch CSV Scoring
# ---------------------------------------------------------------------------
@app.post("/api/v1/underwrite/batch")
async def batch_underwrite(
    file: UploadFile = File(...),
    claims: dict = Depends(require_permission("batch")),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a valid .csv file.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Batch CSV exceeds 10 MB limit.")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty.")

    df = df.head(500).copy()
    if "DAYS_EMPLOYED" in df.columns:
        df.loc[df["DAYS_EMPLOYED"] == 365243, "DAYS_EMPLOYED"] = np.nan

    for feat in ARTIFACTS["feature_names"]:
        if feat not in df.columns:
            df[feat] = np.nan

    X_batch = df[ARTIFACTS["feature_names"]]
    probs = ARTIFACTS["model"].predict_proba(X_batch)[:, 1]
    scores = np.round((1.0 - probs) * 100.0, 1)

    anomaly_scores = ARTIFACTS["isolation_forest"].decision_function(X_batch[ARTIFACTS["anomaly_columns"]])
    is_anomalous = ARTIFACTS["isolation_forest"].predict(X_batch[ARTIFACTS["anomaly_columns"]]) == -1

    id_col = "SK_ID_CURR" if "SK_ID_CURR" in df.columns else ("applicant_id" if "applicant_id" in df.columns else None)
    results = []
    for idx in range(len(df)):
        app_id = str(df.iloc[idx][id_col]) if id_col else f"BATCH_{idx + 1}"
        score = float(scores[idx])
        prob = float(probs[idx])
        anom = bool(is_anomalous[idx])

        if anom:
            decision = "FLAGGED_FOR_MANUAL_REVIEW"
        elif score >= 60.0:
            decision = "APPROVED"
        elif score >= 45.0:
            decision = "CONDITIONAL_APPROVAL"
        else:
            decision = "DECLINED"

        results.append({
            "applicant_id": app_id,
            "credit_risk_score": score,
            "default_probability": round(prob, 4),
            "anomaly_score": round(float(anomaly_scores[idx]), 4),
            "is_anomalous": anom,
            "decision": decision,
        })

    summary = {
        "total_processed": len(results),
        "approved": sum(1 for r in results if r["decision"] == "APPROVED"),
        "conditional": sum(1 for r in results if r["decision"] == "CONDITIONAL_APPROVAL"),
        "manual_review": sum(1 for r in results if r["decision"] == "FLAGGED_FOR_MANUAL_REVIEW"),
        "declined": sum(1 for r in results if r["decision"] == "DECLINED"),
    }

    return {"summary": summary, "results": results}


# ---------------------------------------------------------------------------
# Tab 4: Audit History, Fairness Analytics & Model Retraining
# ---------------------------------------------------------------------------
@app.get("/api/v1/audit-history")
def get_all_audit_history(claims: dict = Depends(require_permission("view_history"))):
    return {"items": AUDIT_HISTORY[:100]}


@app.get("/api/v1/decision-history/{applicant_id}")
def decision_history(applicant_id: str, claims: dict = Depends(require_permission("view_history"))):
    return {"applicant_id": applicant_id, "history": get_history(applicant_id)}


@app.get("/api/v1/fairness-audit")
def audit_fairness(claims: dict = Depends(require_permission("fairness_audit"))):
    if not os.path.exists(config.HOME_CREDIT_TEST_PATH):
        raise HTTPException(status_code=404, detail="Home Credit application_test.csv not found.")
    df = pd.read_csv(config.HOME_CREDIT_TEST_PATH).head(5000)
    return fairness_agent.audit_home_credit(df)


@app.post("/api/v1/admin/retrain")
def trigger_retrain(claims: dict = Depends(require_permission("retrain"))):
    train_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train_model.py")
    if not os.path.exists(train_script):
        raise HTTPException(status_code=404, detail="train_model.py not found.")

    proc = subprocess.run(
        [sys.executable, train_script],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {proc.stderr[-800:]}")

    reload_model_artifacts()
    return {
        "success": True,
        "triggered_by": claims["sub"],
        "output": proc.stdout[-1500:],
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)