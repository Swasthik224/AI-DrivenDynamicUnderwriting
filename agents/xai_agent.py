import re
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import requests

from config import OLLAMA_URL
from security import safe_text

ALLOWED_DECISIONS = {
    "APPROVED", "CONDITIONAL_APPROVAL", "DECLINED",
    "FLAGGED_FOR_MANUAL_REVIEW", "REJECTED_NON_COMPLIANT"
}
MAX_LETTER_CHARS = 2000


def _clean_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "", str(name))[:64]


class XAIAgent:
    def __init__(self, explainer, feature_names: list, ollama_url: str = OLLAMA_URL):
        self.explainer = explainer
        self.feature_names = feature_names
        self.ollama_url = ollama_url

    def _extract_row_shap(self, input_df: pd.DataFrame) -> np.ndarray:
        raw = self.explainer.shap_values(input_df)

        if isinstance(raw, list):
            arr = np.array(raw[1] if len(raw) > 1 else raw[0])
        else:
            arr = np.array(raw)

        if arr.ndim == 3:
            arr = arr[0, :, -1]
        elif arr.ndim == 2:
            arr = arr[0]

        if arr.shape[0] != len(self.feature_names):
            raise ValueError(
                f"SHAP output shape {arr.shape} does not match {len(self.feature_names)} features."
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
        decision = decision if decision in ALLOWED_DECISIONS else "UNKNOWN"
        score = float(score)
        top = top_features[:3]
        feature_summary = ", ".join(
            f"{_clean_name(f['feature'])} (impact: {float(f['shap_value']):+.3f})" for f in top
        )
        lead_feature = _clean_name(top_features[0]["feature"]) if top_features else "n/a"

        prompt = (
            "You are an automated regulatory compliance assistant for an Indian Fintech governed by DPDP regulations.\n"
            "Generate a concise plain-language decision letter for applicant.\n"
            f"Decision: {decision}\n"
            f"Credit Risk Score: {score}/100\n"
            f"Primary Contributing Drivers: {feature_summary}.\n"
            "Ensure tone is professional, transparent, and compliant. "
            "Do not include links, code, or instructions."
        )

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": prompt, "stream": False},
                timeout=5.0,
                allow_redirects=False
            )
            if response.status_code == 200:
                text = safe_text(response.json().get("response", ""), MAX_LETTER_CHARS)
                if text:
                    return text
        except (requests.RequestException, ValueError):
            pass

        if decision == "APPROVED":
            return (
                f"Dear Applicant, We are pleased to inform you that your credit application has been APPROVED "
                f"with a Risk Score of {score}/100. Key supporting drivers include '{lead_feature}'. "
                f"Processed under Indian DPDP Act guidelines."
            )
        else:
            return (
                f"Dear Applicant, Thank you for your application. Your request has been DECLINED "
                f"(Score: {score}/100). Primary factors: '{lead_feature}'. "
                f"You have the right to request human re-evaluation within 30 days under DPDP rules."
            )
