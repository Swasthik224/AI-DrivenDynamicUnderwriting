"""
agents/xai_agent.py
-------------------
Agent 5: Computes SHAP feature attributions and generates natural language explanations.
"""

import requests
import pandas as pd
from typing import List, Dict, Any


class XAIAgent:
    def __init__(self, explainer, feature_names: list, ollama_url: str = "http://localhost:11434"):
        self.explainer = explainer
        self.feature_names = feature_names
        self.ollama_url = ollama_url

    def compute_shap_importance(self, input_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Computes SHAP feature importance attributions."""
        shap_values = self.explainer.shap_values(input_df)[0]

        feature_importance = []
        for feat, val, raw in zip(self.feature_names, shap_values, input_df.iloc[0]):
            feature_importance.append({
                "feature": feat,
                "shap_value": round(float(val), 4),
                "raw_value": float(raw)
            })

        feature_importance.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return feature_importance

    def generate_explanation_letter(self, decision: str, score: float, top_features: List[Dict[str, Any]]) -> str:
        """Calls local Ollama instance or falls back to a deterministic template."""
        feature_summary = ", ".join([f"{f['feature']} (impact: {f['shap_value']:+.3f})" for f in top_features[:3]])

        prompt = (
            f"You are an automated regulatory compliance assistant for an Indian Fintech governed by DPDP regulations.\n"
            f"Generate a concise plain-language decision letter for applicant.\n"
            f"Decision: {decision}\n"
            f"Credit Risk Score: {score}/100\n"
            f"Primary Contributing Drivers: {feature_summary}.\n"
            f"Ensure tone is professional, transparent, and compliant."
        )

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": prompt, "stream": False},
                timeout=2.0
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass  # Fallback to template if Ollama is unreachable

        if decision == "APPROVED":
            return (
                f"Dear Applicant, We are pleased to inform you that your credit application has been APPROVED "
                f"with a Risk Score of {score}/100. Key supporting drivers include '{top_features[0]['feature']}'. "
                f"Processed under Indian DPDP Act guidelines."
            )
        else:
            return (
                f"Dear Applicant, Thank you for your application. Your request has been DECLINED "
                f"(Score: {score}/100). Primary factors: '{top_features[0]['feature']}'. "
                f"You have the right to request human re-evaluation within 30 days under DPDP rules."
            )