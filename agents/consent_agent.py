class ConsentAgent:
    def __init__(self, regulation_name: str = "Indian DPDP Act 2023"):
        self.regulation_name = regulation_name

    def verify_consent(self, consent_given: bool, applicant_id: str) -> dict:
        if consent_given is not True:
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
