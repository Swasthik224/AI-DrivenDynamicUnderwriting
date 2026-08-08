"""
decision_log.py
----------------
Minimal append-only decision log for demo purposes and DPDP-style
accountability. Swap for a real DB in production.
"""

import csv
import os
from datetime import datetime, timezone

LOG_PATH = "decision_log.csv"
FIELDS = [
    "timestamp", "applicant_id", "decision", "credit_risk_score",
    "risk_tier", "fraud_risk_level", "self_check_passed"
]


def log_decision(record: dict):
    file_exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **{k: record.get(k) for k in FIELDS if k != "timestamp"}
        })


def get_history(applicant_id: str) -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["applicant_id"] == applicant_id]
    return rows