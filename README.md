# AI-Driven Dynamic Underwriting Using Alternative Data

> **An AI-powered underwriting platform that predicts customer credit risk using traditional financial data and consent-based alternative data, providing dynamic risk scoring, explainable AI, fraud detection, fairness auditing, and continuous risk recalculation.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue.svg"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-green.svg"/>
  <img src="https://img.shields.io/badge/XGBoost-ML-orange.svg"/>
  <img src="https://img.shields.io/badge/SHAP-ExplainableAI-red.svg"/>
  <img src="https://img.shields.io/badge/IsolationForest-Fraud-purple.svg"/>
  <img src="https://img.shields.io/badge/License-MIT-brightgreen.svg"/>
</p>

---

# 📌 Problem Statement

Traditional underwriting primarily depends on bureau scores and historical financial records, excluding valuable behavioral and digital signals.

This project introduces an **AI-powered Dynamic Underwriting Engine** that combines traditional financial metrics with **consented alternative data** to provide:

* Dynamic Credit Risk Scoring
* Explainable AI (XAI)
* Fraud Detection
* Fairness Auditing
* Continuous Risk Updates
* DPDP-Compliant Consent Verification

---

# 🎯 Objectives

* Predict customer credit risk using traditional + alternative data.
* Generate an explainable dynamic risk score.
* Detect fraudulent or anomalous applications.
* Continuously update customer risk as behavior changes.
* Ensure fairness across demographic groups.
* Process only consented data under Indian DPDP guidelines.

---

# ✨ Features

## ✅ Dynamic AI Underwriting

* Traditional Credit Score Analysis
* Alternative Data Analysis
* Risk Probability Prediction
* Dynamic Credit Score (0–100)

---

## ✅ Alternative Data Signals

Current implementation includes:

* Utility Payment Punctuality
* Monthly Income
* Mobile Wallet Transaction Frequency
* E-commerce Spending
* Gig Income Stability
* Digital Footprint Consistency
* Debt-to-Income Ratio
* Existing Loans

---

## ✅ Explainable AI

* SHAP Feature Importance
* Plain-language Decision Letter
* Local LLM (Ollama) Support
* Regulatory Friendly Explanations

---

## ✅ Fraud Detection

Isolation Forest based anomaly detection.

Detects:

* Suspicious Digital Behaviour
* Unusual Spending Patterns
* Abnormal Wallet Usage
* Digital Footprint Inconsistency

---

## ✅ Fairness Audit

Evaluates model fairness using:

* 80% Rule (Disparate Impact Ratio)
* Gender Bias Analysis
* Age Group Bias Analysis

---

## ✅ Dynamic Risk Recalculation

Customer behavior updates instantly modify:

* Utility Payment Behaviour
* Gig Income Stability

The system recalculates:

* New Risk Score
* Score Difference
* Updated Decision

---

## ✅ Consent Verification

The platform processes alternative data **only when explicit user consent is provided**, ensuring compliance with the **Digital Personal Data Protection (DPDP) Act, 2023**.

---

# 🏗️ Project Architecture

```
                        Applicant
                            │
                            ▼
                 Consent Verification Agent
                            │
                            ▼
               Feature Extraction Pipeline
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
 Credit Risk Model                    Fraud Detection
     (XGBoost)                        (Isolation Forest)
        │                                       │
        └───────────────┬───────────────────────┘
                        ▼
              Explainability Agent
                  (SHAP + LLM)
                        │
                        ▼
               Fairness Audit Agent
                        │
                        ▼
              Final Underwriting Decision
```

---

# 🤖 AI Agents

## 1️⃣ Consent Agent

Responsibilities

* Verify applicant consent
* Enforce DPDP compliance
* Prevent unauthorized processing

---

## 2️⃣ Fraud Detection Agent

Uses:

* Isolation Forest

Responsibilities

* Detect digital anomalies
* Flag suspicious applications
* Generate fraud confidence score

---

## 3️⃣ Explainability Agent

Uses:

* SHAP
* Ollama (Local LLM)

Responsibilities

* Compute feature importance
* Explain every prediction
* Generate regulatory decision letters

---

## 4️⃣ Fairness Agent

Responsibilities

* Audit demographic fairness
* Compute Disparate Impact Ratio
* Verify compliance with the 80% Rule

---

# 🧠 Machine Learning Pipeline

```
Synthetic Dataset
        │
        ▼
Data Cleaning
        │
        ▼
Feature Engineering
        │
        ▼
Train/Test Split
        │
        ▼
XGBoost Training
        │
        ▼
Model Evaluation
        │
        ▼
SHAP Explainer
        │
        ▼
Model Serialization
```

---

# 📊 Dataset

A realistic synthetic underwriting dataset was generated consisting of:

* Traditional Credit Information
* Alternative Financial Signals
* Digital Behaviour
* Consent Status
* Demographic Metadata
* Default Labels

### Traditional Features

* Traditional Credit Score
* Monthly Income
* Debt-to-Income Ratio
* Existing Loans

### Alternative Features

* Utility Payment Punctuality
* Mobile Wallet Transactions
* Gig Income Stability
* Digital Footprint Consistency
* Monthly E-commerce Spending

---

# 📈 Machine Learning Models

## Credit Risk Prediction

* XGBoost Classifier

Predicts:

* Probability of Default
* Credit Risk Score

---

## Fraud Detection

* Isolation Forest

Detects:

* Fraud
* Digital Anomalies
* Suspicious Behaviour

---

## Explainability

* SHAP Tree Explainer

Provides:

* Global Feature Importance
* Local Feature Attribution
* Decision Transparency

---

# ⚙️ Tech Stack

## Backend

* FastAPI
* Python

## Dashboard

* Flask
* HTML
* Tailwind CSS
* Plotly

## Machine Learning

* XGBoost
* SHAP
* Isolation Forest
* Scikit-learn

## Data

* Pandas
* NumPy

## Local LLM

* Ollama
* Llama 3.2

## Model Serialization

* Joblib

---

# 📂 Project Structure

```
AI-Underwriting/
│
├── agents/
│   ├── consent_agent.py
│   ├── fraud_agent.py
│   ├── fairness_agent.py
│   └── xai_agent.py
│
├── app.py
├── dashboard_flask.py
├── generate_dataset.py
├── train_model.py
├── fairness_audit.py
│
├── underwriting_dataset.csv
├── underwriting_artifacts.pkl
│
├── requirements.txt
└── README.md
```

---

# 🚀 API Endpoints

## POST

```
/api/v1/underwrite
```

Performs:

* Credit Scoring
* Fraud Detection
* Explainability
* Final Decision

---

## POST

```
/api/v1/update-behavior
```

Performs

* Dynamic Score Recalculation
* Updated Decision

---

# 📊 Output Example

```json
{
  "applicant_id": "APP_1042",
  "decision": "APPROVED",
  "credit_risk_score": 81.4,
  "default_probability": 0.186,
  "anomaly_flag": false,
  "dpdp_consent_verified": true,
  "top_shap_drivers": [
    {
      "feature": "traditional_score",
      "shap_value": -0.51
    },
    {
      "feature": "utility_pay_punctuality",
      "shap_value": -0.34
    }
  ]
}
```

---

# 📊 Dashboard

The dashboard provides:

* Dynamic Risk Score
* Fraud Status
* SHAP Visualization
* AI Decision Letter
* Applicant Information
* Interactive Controls

---

# 🔒 Security & Privacy

* DPDP Consent Verification
* Consent-based Processing
* Explainable AI
* Bias Auditing
* Human-readable Decisions

---

# 📈 Future Enhancements

* LinkedIn & GitHub Signals
* Employment Verification APIs
* Education Verification
* Device Trust Score
* UPI Behaviour Analytics
* Browser Fingerprinting
* Real-time Streaming Updates
* Fairlearn Integration
* AI Fairness 360 Metrics
* Docker Deployment
* Kubernetes Support
* CI/CD Pipeline
* PostgreSQL Integration
* Redis Caching

---

# 👥 Contributors

Developed as part of an **AI Hackathon** focused on building responsible, explainable, and privacy-preserving AI underwriting systems.

---

# 📄 License

This project is intended for educational and hackathon purposes.
