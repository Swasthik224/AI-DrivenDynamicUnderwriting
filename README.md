# AI-Driven Dynamic Underwriting Using Alternative Data

> A multi-agent underwriting prototype that scores credit risk from traditional financial data and consent-based alternative data, with explainable decisions, fraud detection, fairness auditing, what-if re-scoring and MCP tool access.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue.svg"/>
  <img src="https://img.shields.io/badge/FastAPI-REST-green.svg"/>
  <img src="https://img.shields.io/badge/MCP-FastMCP-teal.svg"/>
  <img src="https://img.shields.io/badge/XGBoost-ML-orange.svg"/>
  <img src="https://img.shields.io/badge/SHAP-ExplainableAI-red.svg"/>
  <img src="https://img.shields.io/badge/IsolationForest-Fraud-purple.svg"/>
</p>

---

## 📌 Problem Statement

Traditional underwriting relies mainly on bureau scores and historical financial records, which excludes valuable behavioural and digital signals.

This project combines traditional financial metrics with **consented alternative data** to provide:

* Dynamic credit-risk scoring (0–100)
* Explainable decisions (SHAP and a plain-language letter)
* Fraud and anomaly detection
* Fairness auditing (80% rule)
* Continuous risk updates (what-if re-scoring)
* Consent verification aligned to India's DPDP Act 2023

---

## 🎯 Objectives

* Predict credit risk using traditional and alternative data.
* Generate an explainable risk score.
* Detect fraudulent or anomalous applications.
* Re-score an applicant when a behavioural metric changes.
* Audit approval rates across gender and age groups.
* Process data only when the consent flag is true.

---

## ⚠️ Current Status

This is a hackathon and teaching prototype. It runs end to end, but:

* The model is trained on **synthetic data only**.
* The supplied dataset contains **one default in 2,000 rows**, so the shipped model returns the same probability of default (0.00068) and credit-risk score (99.9) for every input. Decisions currently differ only because of the fraud rules and Isolation Forest. SHAP drivers and fairness results are therefore not meaningful until the dataset is regenerated with a realistic default rate (the latent risk formula in `generate_dataset.py` needs a positive offset).
* Consent is a Boolean gate, not a full DPDP compliance framework.
* Do not use it for real lending decisions.

---

## ✨ Features

### Dynamic AI Underwriting

* XGBoost probability of default, converted to `credit_risk_score = (1 − PD) × 100`
* Risk tiers: `TIER_1_EXCELLENT` (75+), `TIER_2_GOOD` (60+), `TIER_3_MODERATE` (45+), `TIER_4_HIGH_RISK`

### Alternative Data Signals

* UPI monthly transaction volume
* BNPL repayment rate
* Utility payment punctuality
* Telecom recharge regularity
* E-commerce monthly spend and return rate
* Gig income stability
* Digital footprint consistency
* Device change frequency
* Mobile wallet transaction frequency

Traditional inputs: bureau-style score, monthly income, debt-to-income ratio, number of existing loans.

### Explainable AI

* SHAP feature attributions (top four drivers returned)
* Decision letter drafted by a local Ollama model (`llama3.2`, 5-second timeout) with a fixed fallback template

### Fraud Detection

* Isolation Forest on three signals: digital footprint consistency, device change frequency, e-commerce return rate
* Heuristic flags: `HIGH_DEVICE_TURNOVER`, `SUSPICIOUS_ECOM_RETURN_PATTERN`, `INCONSISTENT_IDENTITY_FOOTPRINT`
* Two or more flags give `CRITICAL`; an anomaly with fewer flags gives `ELEVATED`

### Self-Review

* Rules-based `ReviewAgent` checks score-band consistency, fraud/approval conflicts, protected terms in SHAP drivers and the letter text
* If the review fails and the decision is `APPROVED`, it becomes `FLAGGED_FOR_MANUAL_REVIEW`

### Fairness Audit

* Disparate-impact ratio, demographic-parity difference and 80% rule by gender (reference `Male`) and age group (reference `25_50`)
* Approval is defined as score ≥ 60, matching the live policy
* Gender and age group are **not** model inputs

### Dynamic Risk Recalculation

`POST /api/v1/event-update` changes one metric (value 0–1), re-scores the applicant and returns the original score, new score, delta and new decision. It is a what-if simulation: fraud is assumed clean and consent is assumed true.

### MCP Server

Six tools and one resource over streamable HTTP (see below).

---

## 🏗️ Architecture

```
                         Client / Dashboard
                                │
                                ▼
                     FastAPI  (app.py, :8000)
                                │
   ┌──────────┬─────────────────┼───────────────┬──────────────┐
   ▼          ▼                 ▼               ▼              ▼
Consent    Alt-Data       Fraud (IF + rules)  Risk (XGBoost)  MCP lookup
Agent      Agent               │                  │          (get_applicant_data,
   │          │                └────────┬─────────┘           diagnostic only)
   └──────────┴─────────────────────────▼
                                  Decision Agent
                                        │
                                        ▼
                         XAI Agent (SHAP + Ollama letter)
                                        │
                                        ▼
                         Review Agent (self-check, fail-safe)
                                        │
                                        ▼
                        decision_log.csv  +  JSON response

Fairness Agent: separate endpoint and MCP tool, not part of /underwrite.
```

Request order in `/api/v1/underwrite`: validate → consent (403 if false) → MCP lookup (continues on failure) → feature preparation (missing features become 0) → alt-data, fraud and risk (sequential) → decision → SHAP → letter → review → log → response.

---

## 🤖 Agents

| Agent | File | Role |
| --- | --- | --- |
| ConsentAgent | `agents/consent_agent.py` | Boolean consent gate; 403 when false |
| AltDataAgent | `agents/alt_data_agent.py` | Composite score (0–100) and two footprint/reliability indices |
| FraudAgent | `agents/fraud_agent.py` | Isolation Forest plus three heuristic rules |
| RiskPredictionAgent | `agents/risk_prediction_agent.py` | PD, credit-risk score and tier |
| DecisionAgent | `agents/decision_agent.py` | Policy: consent → fraud override → score bands |
| XAIAgent | `agents/xai_agent.py` | SHAP drivers and decision letter |
| FairnessAgent | `agents/fairness_agent.py` | Group approval rates and DIR |
| ReviewAgent | `agents/review_agent.py` | Rules-based pre-release self-check |

### Decision policy

| Condition | Outcome |
| --- | --- |
| Consent false | `REJECTED_NON_COMPLIANT` |
| Anomalous or `CRITICAL` fraud | `FLAGGED_FOR_MANUAL_REVIEW` |
| Score ≥ 60 | `APPROVED` |
| Score 45–59.9 | `CONDITIONAL_APPROVAL` |
| Score < 45 | `DECLINED` |

---

## 🧠 Machine Learning Pipeline

```
generate_dataset.py  →  underwriting_dataset.csv
        │
        ▼
train_model.py
  • keep consented rows
  • 14 model features (gender / age_group excluded)
  • 80/20 split
  • XGBoost (150 trees, depth 4, lr 0.05)
  • Isolation Forest (100 trees, contamination 0.05)
  • SHAP TreeExplainer
        │
        ▼
underwriting_artifacts.pkl  (joblib)
```

---

## 📊 Dataset

`generate_dataset.py` creates 2,000 synthetic applicants (seed 42): identifiers, gender, age group, consent (about 92% true), traditional and alternative signals, and a `default_flag` derived from a latent risk formula with noise. Demographic columns are kept only for fairness auditing.

---

## ⚙️ Tech Stack

| Area | Tools |
| --- | --- |
| Backend | Python, FastAPI, Pydantic, uvicorn |
| MCP | FastMCP (`mcp` package), streamable HTTP |
| Dashboard | Flask, Tailwind CSS (CDN), plain JavaScript |
| ML | XGBoost, scikit-learn (Isolation Forest), SHAP |
| Data | pandas, NumPy, joblib |
| Local LLM | Ollama, Llama 3.2 (optional) |

---

## 📂 Project Structure

```
underwriting_engine/
│
├── agents/
│   ├── __init__.py
│   ├── alt_data_agent.py
│   ├── consent_agent.py
│   ├── decision_agent.py
│   ├── fairness_agent.py
│   ├── fraud_agent.py
│   ├── review_agent.py
│   ├── risk_prediction_agent.py
│   └── xai_agent.py
│
├── app.py                 # FastAPI app (port 8000)
├── mcp_server.py          # MCP server (port 8001)
├── dashboard_flask.py     # Demo console (port 5000)
├── decision_log.py        # Append-only CSV log helpers
├── generate_dataset.py
├── train_model.py
├── fairness_audit.py      # Standalone audit script
│
├── underwriting_dataset.csv
├── underwriting_artifacts.pkl
├── decision_log.csv
│
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

Run all commands from the project root (paths are relative).

```bash
pip install fastapi uvicorn pandas numpy scikit-learn xgboost shap joblib pydantic requests mcp flask

python generate_dataset.py
python train_model.py

ollama pull llama3.2          # optional, for generated letters

python mcp_server.py          # terminal 1, port 8001
python app.py                 # terminal 2, port 8000
python dashboard_flask.py     # terminal 3, port 5000
```

Open `http://127.0.0.1:8000/docs` for Swagger UI and `http://localhost:5000` for the dashboard.

---

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/underwrite` | Full pipeline; 403 when consent is false |
| POST | `/api/v1/event-update` | What-if re-score after one metric changes |
| GET | `/api/v1/fairness-audit` | Gender and age-group fairness metrics |
| GET | `/api/v1/decision-history/{applicant_id}` | Logged decisions for an applicant |
| GET | `/api/v1/mcp-status` | MCP connection check and tool list |
| GET | `/api/v1/mcp-applicant/{applicant_id}` | Direct call to `get_applicant_data` |

### Example `/api/v1/underwrite` response (abridged, values illustrative)

```json
{
  "applicant_id": "APP_1042",
  "mcp": { "server": "http://127.0.0.1:8001/mcp", "status": "SUCCESS", "result": { } },
  "decision": "APPROVED",
  "decision_reason": "Low default risk meeting auto-approval thresholds.",
  "credit_risk_score": 81.4,
  "risk_tier": "TIER_1_EXCELLENT",
  "default_probability": 0.186,
  "alt_data_metrics": {
    "alt_composite_score": 82.5,
    "financial_footprint_index": 0.95,
    "digital_reliability_index": 0.93
  },
  "fraud_assessment": {
    "is_anomalous": false,
    "ml_anomaly_score": 0.133,
    "fraud_risk_level": "LOW",
    "triggered_flags": []
  },
  "top_shap_drivers": [
    { "feature": "traditional_score", "shap_value": -0.51, "raw_value": 620.0 }
  ],
  "explanation_letter": "Dear Applicant, ...",
  "self_check": { "self_check_passed": true, "issues": [], "note": "..." }
}
```

---

## 🧩 MCP Tools

Served at `http://127.0.0.1:8001/mcp`.

| Tool / resource | Purpose |
| --- | --- |
| `get_applicant_data(applicant_id)` | Dataset row for an applicant (no consent check) |
| `get_alternative_data(applicant_id)` | Alt-data metrics (requires consent) |
| `run_risk_prediction(applicant_id)` | XGBoost risk result (requires consent) |
| `run_fraud_check(applicant_id)` | Fraud result (requires consent) |
| `get_decision_history(applicant_id)` | Rows from `decision_log.csv` |
| `run_fairness_audit()` | Fairness audit over the dataset |
| `underwriting://system` | Resource describing the system |

---

## 📊 Dashboard

`dashboard_flask.py` serves a single-page console with four preset applicants (custom, gig worker, salaried, suspicious-pattern test), a consent toggle, numeric inputs and sliders. It posts to `http://localhost:8000/api/v1/underwrite` and shows the decision, score, default probability, fraud assessment, SHAP drivers and the letter.

---

## 🔒 Security & Privacy

Implemented in the prototype:

* Consent gate before scoring
* Protected attributes excluded from model inputs and audited separately
* Review check for protected terms in SHAP drivers
* Decision log for accountability

Not yet implemented (needed before any real use): authentication, restricted CORS, encrypted and access-controlled storage, a durable consent record with withdrawal handling, a transactional audit database, and legal review.

---

## 🛠️ Known Limitations

* Near-constant model output with the supplied dataset (see Current Status)
* Missing model features default to 0
* The letter is not regenerated if the self-check downgrades an approval
* Fallback letter labels every non-approval as "DECLINED"
* `fairness_audit.py` uses PD < 0.45 for approval, while the live policy uses score ≥ 60
* `/event-update` skips real consent and fraud checks
* `requirements.txt` omits `mcp` and `flask` and lists unused `fairlearn`, `streamlit` and `plotly`

---

## 📈 Future Enhancements

* Regenerate data with a realistic default rate and add calibration checks
* Shared policy function used by scoring, audits and tests
* Durable consent records and withdrawal handling
* Fairlearn and AI Fairness 360 metrics
* Real-time streaming updates and richer behavioural signals
* PostgreSQL audit log, Redis caching, Docker and CI/CD

---

## 👥 Contributors

Developed as part of an **AI Hackathon** focused on responsible, explainable and privacy-preserving AI underwriting.

---

## 📄 License

This project is intended for educational and hackathon purposes.
