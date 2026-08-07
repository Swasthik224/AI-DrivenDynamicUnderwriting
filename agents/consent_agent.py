"""
agents/consent_agent.py
------------------------
Agent 1: Verifies explicit user consent flags under DPDP requirements
before allowing processing of alternative data signals.
"""

from pydantic import BaseModel, Field


class ConsentAgent:
    def __init__(self, regulation_name: str = "Indian DPDP Act 2023"):
        self.regulation_name = regulation_name

    def verify_consent(self, consent_given: bool, applicant_id: str) -> dict:
        """
        Validates whether the user provided explicit consent.
        """
        if not consent_given:
            return {
                "verified": False,
                "applicant_id": applicant_id,
                "status_code": 403,
                "message": f"Processing Denied under {self.regulation_name}: Applicant consent flag is FALSE."
            }

        return {
            "verified": True,
            "applicant_id": applicant_id,
            "status_code": 200,
            "message": f"Consent verified under {self.regulation_name} guidelines."
        }