"""
app.py - Multi-Agent Event-Driven FastAPI Backend
with MCP Client Integration
"""

import os
import joblib
import pandas as pd
import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
from typing import Optional

# ============================================================
# MCP 1.30.0 CLIENT
# ============================================================

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# ============================================================
# EXISTING AGENTS
# ============================================================

from agents import (
    ConsentAgent,
    AltDataAgent,
    FraudAgent,
    RiskPredictionAgent,
    XAIAgent,
    FairnessAgent,
    DecisionAgent,
    ReviewAgent
)

from decision_log import log_decision, get_history


# ============================================================
# CONFIGURATION
# ============================================================

ARTIFACTS = None

MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


# ============================================================
# AGENTS
# ============================================================

consent_agent = ConsentAgent()
alt_agent = AltDataAgent()
decision_agent = DecisionAgent()
review_agent = ReviewAgent()

fraud_agent = None
risk_agent = None
xai_agent = None
fairness_agent = None


# ============================================================
# MCP TOOL CALLER
# ============================================================

async def call_mcp_tool(
    tool_name: str,
    arguments: dict
):
    """
    Connect to the MCP server and call one MCP tool.

    MCP Server:
        http://127.0.0.1:8001/mcp

    MCP version:
        1.30.0
    """

    try:

        async with streamable_http_client(
            MCP_SERVER_URL
        ) as (
            read_stream,
            write_stream,
            _
        ):

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                # Initialize MCP session
                await session.initialize()

                print(
                    f"🔌 MCP connected: {MCP_SERVER_URL}"
                )

                # Call MCP tool
                result = await session.call_tool(
                    tool_name,
                    arguments=arguments
                )

                print(
                    f"✅ MCP tool executed: {tool_name}"
                )

                return result

    except Exception as e:

        print(
            f"❌ MCP tool error "
            f"'{tool_name}': {e}"
        )

        raise


# ============================================================
# MCP RESULT CONVERTER
# ============================================================

def extract_mcp_result(result):
    """
    Converts an MCP CallToolResult into a JSON-friendly
    representation for FastAPI responses.
    """

    # Structured result
    if hasattr(result, "structured_content"):

        structured = result.structured_content

        if structured is not None:
            return structured

    # Content blocks
    if hasattr(result, "content"):

        output = []

        for item in result.content:

            if hasattr(item, "text"):

                output.append(
                    item.text
                )

            else:

                output.append(
                    str(item)
                )

        return output

    return str(result)


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global ARTIFACTS
    global fraud_agent
    global risk_agent
    global xai_agent
    global fairness_agent

    if os.path.exists(
        "underwriting_artifacts.pkl"
    ):

        ARTIFACTS = joblib.load(
            "underwriting_artifacts.pkl"
        )

        fraud_agent = FraudAgent(
            ARTIFACTS["isolation_forest"],
            ARTIFACTS["anomaly_columns"]
        )

        risk_agent = RiskPredictionAgent(
            ARTIFACTS["model"],
            ARTIFACTS["feature_names"]
        )

        xai_agent = XAIAgent(
            ARTIFACTS["explainer"],
            ARTIFACTS["feature_names"]
        )

        fairness_agent = FairnessAgent(
            ARTIFACTS["model"],
            ARTIFACTS["feature_names"]
        )

        print(
            "✅ All Autonomous Agents Initialized Successfully."
        )

    else:

        raise FileNotFoundError(
            "Run 'python train_model.py' first."
        )

    yield


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Enterprise Agentic Underwriting Pipeline",
    lifespan=lifespan
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# APPLICANT SCHEMA
# ============================================================

class FullApplicantSchema(BaseModel):

    applicant_id: str = Field(
        "APP_1042",
        json_schema_extra={
            "example": "APP_1042"
        }
    )

    gender: str = Field(
        "Female",
        json_schema_extra={
            "example": "Female"
        }
    )

    age_group: str = Field(
        "25_50",
        json_schema_extra={
            "example": "25_50"
        }
    )

    consent_given: bool = Field(
        True,
        json_schema_extra={
            "example": True
        }
    )

    traditional_score: float = Field(
        680.0,
        ge=300,
        le=850
    )

    monthly_income_inr: float = Field(
        85000.0,
        ge=0
    )

    debt_to_income_ratio: float = Field(
        0.28,
        ge=0.0,
        le=1.0
    )

    upi_monthly_tx_volume: int = Field(
        42,
        ge=0
    )

    bnpl_repayment_rate: float = Field(
        0.95,
        ge=0.0,
        le=1.0
    )

    utility_pay_punctuality: float = Field(
        0.90,
        ge=0.0,
        le=1.0
    )

    telecom_recharge_regularity: float = Field(
        0.88,
        ge=0.0,
        le=1.0
    )

    ecommerce_monthly_spend: float = Field(
        12000.0,
        ge=0
    )

    ecommerce_return_rate: float = Field(
        0.08,
        ge=0.0,
        le=1.0
    )

    gig_income_stability_index: float = Field(
        0.82,
        ge=0.0,
        le=1.0
    )

    digital_footprint_consistency: float = Field(
        0.91,
        ge=0.0,
        le=1.0
    )

    device_change_frequency: int = Field(
        1,
        ge=0
    )

    # Optional fields
    num_existing_loans: Optional[int] = 0

    mobile_wallet_tx_freq: Optional[int] = 0


# ============================================================
# BEHAVIORAL EVENT SCHEMA
# ============================================================

class BehavioralEventPayload(BaseModel):

    applicant_id: str

    event_type: str = Field(
        ...,
        json_schema_extra={
            "example":
                "UTILITY_PAYMENT_MISSED"
        }
    )

    metric_updated: str = Field(
        ...,
        json_schema_extra={
            "example":
                "utility_pay_punctuality"
        }
    )

    new_value: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )

    applicant_data: FullApplicantSchema


# ============================================================
# FEATURE PREPARATION
# ============================================================

def prepare_feature_df(
    data_dict: dict
) -> pd.DataFrame:

    """
    Safely aligns dictionary data with trained
    model feature expectations.
    """

    clean_dict = data_dict.copy()

    for feat in ARTIFACTS["feature_names"]:

        if feat not in clean_dict:

            clean_dict[feat] = 0

    return pd.DataFrame(
        [clean_dict]
    )[
        ARTIFACTS["feature_names"]
    ]


# ============================================================
# MCP STATUS
# ============================================================

@app.get("/api/v1/mcp-status")
async def mcp_status():

    """
    Tests the connection between FastAPI and MCP server.

    Does not run underwriting.
    """

    try:

        async with streamable_http_client(
            MCP_SERVER_URL
        ) as (
            read_stream,
            write_stream,
            _
        ):

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                await session.initialize()

                tools_result = (
                    await session.list_tools()
                )

                tools = [
                    tool.name
                    for tool in tools_result.tools
                ]

                return {
                    "mcp_connected": True,
                    "mcp_server":
                        MCP_SERVER_URL,
                    "mcp_version":
                        "1.30.0",
                    "tools":
                        tools
                }

    except Exception as e:

        return {
            "mcp_connected": False,
            "mcp_server":
                MCP_SERVER_URL,
            "mcp_version":
                "1.30.0",
            "error":
                str(e)
        }


# ============================================================
# MCP APPLICANT DATA TEST
# ============================================================

@app.get(
    "/api/v1/mcp-applicant/{applicant_id}"
)
async def mcp_applicant(
    applicant_id: str
):

    """
    Directly calls the MCP
    get_applicant_data tool.
    """

    try:

        result = await call_mcp_tool(
            "get_applicant_data",
            {
                "applicant_id":
                    applicant_id
            }
        )

        return {

            "mcp_connected":
                True,

            "applicant_id":
                applicant_id,

            "result":
                extract_mcp_result(result)
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"MCP tool call failed: "
                f"{str(e)}"
            )
        )


# ============================================================
# UNDERWRITING
# ============================================================

@app.post(
    "/api/v1/underwrite",
    status_code=200
)
async def underwrite(
    applicant: FullApplicantSchema
):

    # ========================================================
    # AGENT 1 - CONSENT
    # ========================================================

    c_res = consent_agent.verify_consent(
        applicant.consent_given,
        applicant.applicant_id
    )

    if not c_res["verified"]:

        raise HTTPException(
            status_code=403,
            detail=c_res["message"]
        )

    # ========================================================
    # MCP - APPLICANT DATA
    # ========================================================

    mcp_result = None
    mcp_status = "NOT_CALLED"

    try:

        mcp_result = await call_mcp_tool(
            "get_applicant_data",
            {
                "applicant_id":
                    applicant.applicant_id
            }
        )

        mcp_status = "SUCCESS"

        print(
            "✅ MCP applicant data retrieved:",
            applicant.applicant_id
        )

    except Exception as e:

        # MCP failure does not destroy the existing
        # underwriting pipeline.

        mcp_status = "FAILED"

        print(
            "⚠️ MCP applicant lookup failed:",
            e
        )

    # ========================================================
    # PREPARE APPLICANT DATA
    # ========================================================

    raw_dict = applicant.model_dump()

    input_df = prepare_feature_df(
        raw_dict
    )

    # ========================================================
    # DEBUG
    # ========================================================

    print(
        "DEBUG feature_names:",
        ARTIFACTS["feature_names"]
    )

    print(
        "DEBUG input_df row:\n",
        input_df.iloc[0].to_dict()
    )

    # ========================================================
    # AGENT 2 - ALTERNATIVE DATA
    # ========================================================

    alt_res = alt_agent.process_signals(
        raw_dict
    )

    # ========================================================
    # AGENT 3 - FRAUD
    # ========================================================

    fraud_res = (
        fraud_agent.evaluate_fraud_risk(
            input_df
        )
    )


    risk_res = (
        risk_agent.predict_risk(
            input_df
        )
    )

    decision_res = (
        decision_agent.render_decision(
            risk_res["credit_risk_score"],
            fraud_res,
            applicant.consent_given
        )
    )

    shap_drivers = (
        xai_agent.compute_shap_importance(
            input_df
        )
    )

    letter = (
        xai_agent.generate_explanation_letter(
            decision_res["decision"],
            risk_res["credit_risk_score"],
            shap_drivers
        )
    )


    review_res = review_agent.review(
        decision_res,
        risk_res,
        fraud_res,
        shap_drivers,
        letter
    )


    if not review_res[
        "self_check_passed"
    ]:

        if (
            decision_res["decision"]
            == "APPROVED"
        ):

            decision_res = {

                "decision":
                    "FLAGGED_FOR_MANUAL_REVIEW",

                "reason":
                    (
                        "Self-check failed: "
                        + "; ".join(
                            review_res["issues"]
                        )
                    )
            }


    log_decision({

        "applicant_id":
            applicant.applicant_id,

        "decision":
            decision_res["decision"],

        "credit_risk_score":
            risk_res[
                "credit_risk_score"
            ],

        "risk_tier":
            risk_res["risk_tier"],

        "fraud_risk_level":
            fraud_res[
                "fraud_risk_level"
            ],

        "self_check_passed":
            review_res[
                "self_check_passed"
            ],
    })


    return {

        "applicant_id":
            applicant.applicant_id,

        # MCP information
        "mcp": {

            "server":
                MCP_SERVER_URL,

            "status":
                mcp_status,

            "result":
                extract_mcp_result(
                    mcp_result
                )
                if mcp_result
                else None
        },

        # Decision
        "decision":
            decision_res[
                "decision"
            ],

        "decision_reason":
            decision_res[
                "reason"
            ],

        # Risk
        "credit_risk_score":
            risk_res[
                "credit_risk_score"
            ],

        "risk_tier":
            risk_res[
                "risk_tier"
            ],

        "default_probability":
            risk_res[
                "default_probability"
            ],

        # Alternative data
        "alt_data_metrics":
            alt_res,

        # Fraud
        "fraud_assessment":
            fraud_res,

        # Explainability
        "top_shap_drivers":
            shap_drivers[:4],

        "explanation_letter":
            letter,

        # Review
        "self_check":
            review_res
    }



@app.post(
    "/api/v1/event-update",
    status_code=200
)
def process_behavioral_event(
    event: BehavioralEventPayload
):

    """
    Event-Driven API:
    Processes real-time updates and measures score delta.
    """


    base_data = (
        event.applicant_data.model_dump()
    )

    df_base = prepare_feature_df(
        base_data
    )

    base_score = (
        risk_agent.predict_risk(
            df_base
        )["credit_risk_score"]
    )


    updated_data = base_data.copy()

    updated_data[
        event.metric_updated
    ] = event.new_value

    df_updated = prepare_feature_df(
        updated_data
    )

    updated_risk = (
        risk_agent.predict_risk(
            df_updated
        )
    )

    score_delta = round(
        updated_risk[
            "credit_risk_score"
        ] - base_score,
        1
    )


    new_decision = (
        decision_agent.render_decision(
            updated_risk[
                "credit_risk_score"
            ],
            {
                "is_anomalous": False,
                "fraud_risk_level":
                    "LOW"
            },
            True
        )["decision"]
    )

    return {

        "applicant_id":
            event.applicant_id,

        "event_processed":
            event.event_type,

        "original_score":
            base_score,

        "new_score":
            updated_risk[
                "credit_risk_score"
            ],

        "score_delta":
            score_delta,

        "new_decision":
            new_decision
    }



@app.get(
    "/api/v1/fairness-audit",
    status_code=200
)
def audit_fairness():

    df = pd.read_csv(
        "underwriting_dataset.csv"
    )

    return fairness_agent.audit(
        df
    )



@app.get(
    "/api/v1/decision-history/{applicant_id}",
    status_code=200
)
def decision_history(
    applicant_id: str
):

    """
    Returns logged decisions for an applicant.
    """

    return {

        "applicant_id":
            applicant_id,

        "history":
            get_history(
                applicant_id
            )
    }



if __name__ == "__main__":

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )