
import csv
import os
import json
import hashlib
import threading

from datetime import datetime, timezone
from contextlib import contextmanager

LOG_PATH = os.getenv("DECISION_LOG_PATH", "decision_log.csv")
LOCK_PATH = LOG_PATH + ".lock"

FIELDS = [
    "timestamp",
    "applicant_id",
    "decision",
    "credit_risk_score",
    "risk_tier",
    "fraud_risk_level",
    "self_check_passed",
    "previous_hash",
    "record_hash"
]

GENESIS_HASH = "0" * 64

_thread_lock = threading.RLock()


@contextmanager
def file_lock():
    """
    Cross-platform file lock.
    Uses fcntl on Linux/macOS and msvcrt on Windows.
    """

    os.makedirs(os.path.dirname(os.path.abspath(LOCK_PATH)), exist_ok=True)

    with _thread_lock:
        with open(LOCK_PATH, "a+b") as lock_file:

            if os.name == "nt":
                import msvcrt

                lock_file.seek(0)

                if os.path.getsize(LOCK_PATH) == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)

                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def calculate_hash(record: dict) -> str:
    """
    Generate a SHA-256 hash from a decision record.
    """

    payload = {
        key: record.get(key)
        for key in FIELDS
        if key != "record_hash"
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_record(record: dict):
    """
    Validate the minimum information required for logging.
    """

    if not isinstance(record, dict):
        raise ValueError("Decision record must be a dictionary.")

    applicant_id = record.get("applicant_id")

    if not isinstance(applicant_id, str):
        raise ValueError("Applicant ID must be a string.")

    applicant_id = applicant_id.strip()

    if not applicant_id or len(applicant_id) > 100:
        raise ValueError("Invalid applicant ID.")

    if not all(
        char.isalnum() or char in "_-"
        for char in applicant_id
    ):
        raise ValueError("Applicant ID contains invalid characters.")

    decision = record.get("decision")

    if not isinstance(decision, str) or not decision.strip():
        raise ValueError("Decision is required.")

    score = record.get("credit_risk_score")

    if score is not None:
        try:
            score = float(score)
        except (TypeError, ValueError):
            raise ValueError("Credit risk score must be numeric.")

        if not 0 <= score <= 100:
            raise ValueError("Credit risk score must be between 0 and 100.")


def get_last_hash():
    """
    Retrieve the hash of the latest validly formatted log entry.
    """

    if not os.path.exists(LOG_PATH):
        return GENESIS_HASH

    with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        last_record = None

        for row in reader:
            last_record = row

        if last_record is None:
            return GENESIS_HASH

        return last_record.get("record_hash", "")


def log_decision(record: dict):
    """
    Append a decision to the hash-chained audit log.
    """

    validate_record(record)

    with file_lock():

        file_exists = os.path.exists(LOG_PATH)

        if file_exists and os.path.getsize(LOG_PATH) > 0:
            with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                existing_header = next(reader, [])

            if existing_header != FIELDS:
                raise RuntimeError(
                    "Existing decision log has an incompatible format. "
                    "Back it up and migrate it before using this version."
                )

        previous_hash = get_last_hash()

        if not previous_hash:
            raise RuntimeError("Could not retrieve the previous record hash.")

        new_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "applicant_id": record["applicant_id"].strip(),
            "decision": record["decision"].strip(),
            "credit_risk_score": record.get("credit_risk_score"),
            "risk_tier": record.get("risk_tier"),
            "fraud_risk_level": record.get("fraud_risk_level"),
            "self_check_passed": record.get("self_check_passed"),
            "previous_hash": previous_hash
        }

        new_record["record_hash"] = calculate_hash(new_record)

        with open(LOG_PATH, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            if not file_exists or os.path.getsize(LOG_PATH) == 0:
                writer.writeheader()

            writer.writerow(new_record)
            file.flush()
            os.fsync(file.fileno())


def get_history(applicant_id: str) -> list:
    """
    Return decision history for a specific applicant.
    """

    if not isinstance(applicant_id, str) or not applicant_id.strip():
        raise ValueError("A valid applicant ID is required.")

    with file_lock():

        if not os.path.exists(LOG_PATH):
            return []

        with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames != FIELDS:
                raise RuntimeError("Invalid decision log format.")

            rows = [
                row
                for row in reader
                if row["applicant_id"] == applicant_id.strip()
            ]

        return rows


def verify_log() -> dict:
    """
    Verify the integrity of the complete decision log.

    Checks:
    - Record hash validity.
    - Previous hash linkage.
    - Record ordering.
    """

    with file_lock():

        if not os.path.exists(LOG_PATH):
            return {
                "valid": True,
                "total_records": 0,
                "message": "Decision log does not exist yet."
            }

        previous_hash = GENESIS_HASH
        total_records = 0

        with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames != FIELDS:
                return {
                    "valid": False,
                    "total_records": 0,
                    "message": "Invalid or modified log header."
                }

            for row in reader:
                total_records += 1

                stored_previous_hash = row.get("previous_hash")
                stored_record_hash = row.get("record_hash")

                if stored_previous_hash != previous_hash:
                    return {
                        "valid": False,
                        "total_records": total_records,
                        "message": (
                            f"Hash chain mismatch at record "
                            f"{total_records}."
                        )
                    }

                calculated_hash = calculate_hash(row)

                if stored_record_hash != calculated_hash:
                    return {
                        "valid": False,
                        "total_records": total_records,
                        "message": (
                            f"Record integrity check failed at record "
                            f"{total_records}."
                        )
                    }

                previous_hash = stored_record_hash

        return {
            "valid": True,
            "total_records": total_records,
            "message": "All decision records passed integrity verification."
        }


if __name__ == "__main__":

    result = verify_log()

    print("Decision Log Verification")
    print("-------------------------")
    print(f"Valid: {result['valid']}")
    print(f"Total Records: {result['total_records']}")
    print(f"Message: {result['message']}")
