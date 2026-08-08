"""
agents/xai_agent.py
-------------------
Agent 5: Computes SHAP feature attributions and generates natural language explanations.
"""

import requests
import numpy as np
import pandas as pd
from typing import List, Dict, Any


class XAIAgent:
    def __init__(self, explainer, feature_names: list, ollama_url: str = "http://localhost:11434"):
        self.explainer = explainer
        self.feature_names = feature_names
        self.ollama_url = ollama_url

    def _extract_row_shap(self, input_df: pd.DataFrame) -> np.ndarray:
        """Normalizes shap_values() output across shap/xgboost version differences
        so we always end up with a flat (n_features,) array for the single row."""
        raw = self.explainer.shap_values(input_df)

        # Case 1: list of arrays, one per class -> take positive class (index 1)
        if isinstance(raw, list):
            arr = np.array(raw[1] if len(raw) > 1 else raw[0])
        else:
            arr = np.array(raw)

        # Now arr could be (n_features,), (1, n_features), or (1, n_features, n_classes)
        if arr.ndim == 3:
            # (n_samples, n_features, n_classes) -> row 0, positive class (last index)
            arr = arr[0, :, -1]
        elif arr.ndim == 2:
            # (n_samples, n_features) -> row 0
            arr = arr[0]
        # else already 1D

        if arr.shape[0] != len(self.feature_names):
            raise ValueError(
                f"SHAP output shape {arr.shape} does not match {len(self.feature_names)} features — "
                f"check shap/xgboost version compatibility."
            )
        return arr

    def compute_shap_importance(self, input_df: pd.DataFrame) -> List[Dict[str, Any]]:
        shap_row = self._extract_row_shap(input_df)

        feature_importance = []
        for feat, val, raw in zip(self.feature_names, shap_row, input_df.iloc[0]):
            feature_importance.append({
                "feature": feat,
                "shap_value": round(float(val), 4),
                "raw_value": float(raw)
            })

        feature_importance.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return feature_importance

    def generate_explanation_letter(self, decision: str, score: float, top_features: List[Dict[str, Any]]) -> str:
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
                timeout=5.0
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass

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