
import csv
import os
import json
import hashlib
import threading
import shutil

from datetime import datetime, timezone
from contextlib import contextmanager

LOG_PATH = os.getenv("DECISION_LOG_PATH", "decision_log.csv")
LOCK_PATH = LOG_PATH + ".lock"

LEGACY_FIELDS = [
    "timestamp",
    "applicant_id",
    "decision",
    "credit_risk_score",
    "risk_tier",
    "fraud_risk_level",
    "self_check_passed"
]

FIELDS = LEGACY_FIELDS + [
    "previous_hash",
    "record_hash"
]

GENESIS_HASH = "0" * 64

_thread_lock = threading.RLock()


@contextmanager
def file_lock():
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


def normalize_record(record: dict) -> dict:
    return {
        key: "" if record.get(key) is None else str(record.get(key))
        for key in FIELDS
        if key != "record_hash"
    }


def calculate_hash(record: dict) -> str:
    payload = normalize_record(record)

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def validate_record(record: dict):
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

    if score is not None and score != "":
        try:
            score = float(score)
        except (TypeError, ValueError):
            raise ValueError("Credit risk score must be numeric.")

        if not 0 <= score <= 100:
            raise ValueError("Credit risk score must be between 0 and 100.")


def _verify_log_unlocked() -> dict:
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

            if None in row or any(row.get(field) is None for field in FIELDS):
                return {
                    "valid": False,
                    "total_records": total_records,
                    "message": f"Malformed record at record {total_records}."
                }

            stored_previous_hash = row.get("previous_hash")
            stored_record_hash = row.get("record_hash")

            if stored_previous_hash != previous_hash:
                return {
                    "valid": False,
                    "total_records": total_records,
                    "message": f"Hash chain mismatch at record {total_records}."
                }

            calculated_hash = calculate_hash(row)

            if stored_record_hash != calculated_hash:
                return {
                    "valid": False,
                    "total_records": total_records,
                    "message": f"Record integrity check failed at record {total_records}."
                }

            previous_hash = stored_record_hash

    return {
        "valid": True,
        "total_records": total_records,
        "message": "All decision records passed integrity verification."
    }


def migrate_legacy_log() -> dict:
    with file_lock():
        if not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0:
            return {
                "success": True,
                "migrated": False,
                "message": "No existing decision records to migrate."
            }

        with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames == FIELDS:
                return {
                    "success": True,
                    "migrated": False,
                    "message": "Decision log already uses the current format."
                }

            if reader.fieldnames != LEGACY_FIELDS:
                raise RuntimeError(
                    "Unsupported decision log format. "
                    "Original file has not been modified."
                )

            legacy_records = list(reader)

        migrated_records = []
        previous_hash = GENESIS_HASH

        for index, old_record in enumerate(legacy_records, start=1):
            if None in old_record or any(
                old_record.get(field) is None
                for field in LEGACY_FIELDS
            ):
                raise RuntimeError(
                    f"Malformed legacy decision record at row {index}."
                )

            new_record = {
                field: old_record[field]
                for field in LEGACY_FIELDS
            }

            new_record["previous_hash"] = previous_hash
            new_record["record_hash"] = calculate_hash(new_record)

            migrated_records.append(new_record)
            previous_hash = new_record["record_hash"]

        backup_path = LOG_PATH + ".legacy.bak"

        if os.path.exists(backup_path):
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            backup_path = LOG_PATH + f".legacy.{timestamp}.bak"

        shutil.copy2(LOG_PATH, backup_path)

        temp_path = LOG_PATH + ".tmp"

        try:
            with open(temp_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=FIELDS
                )

                writer.writeheader()
                writer.writerows(migrated_records)

                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_path, LOG_PATH)

        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return {
            "success": True,
            "migrated": True,
            "total_records": len(migrated_records),
            "backup_path": backup_path,
            "message": "Legacy decision log migrated successfully."
        }


def get_last_hash():
    if not os.path.exists(LOG_PATH):
        return GENESIS_HASH

    with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != FIELDS:
            raise RuntimeError("Invalid decision log format.")

        last_record = None

        for row in reader:
            last_record = row

        if last_record is None:
            return GENESIS_HASH

        return last_record.get("record_hash", "")


def log_decision(record: dict):
    validate_record(record)
    migrate_legacy_log()

    with file_lock():
        integrity = _verify_log_unlocked()

        if not integrity["valid"]:
            raise RuntimeError(integrity["message"])

        previous_hash = get_last_hash()

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

        new_record = {
            key: "" if value is None else str(value)
            for key, value in new_record.items()
        }

        new_record["record_hash"] = calculate_hash(new_record)

        file_exists = os.path.exists(LOG_PATH)

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
    if not isinstance(applicant_id, str) or not applicant_id.strip():
        raise ValueError("A valid applicant ID is required.")

    migrate_legacy_log()

    with file_lock():
        integrity = _verify_log_unlocked()

        if not integrity["valid"]:
            raise RuntimeError(integrity["message"])

        if not os.path.exists(LOG_PATH):
            return []

        with open(LOG_PATH, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            return [
                row
                for row in reader
                if row["applicant_id"] == applicant_id.strip()
            ]


def verify_log() -> dict:
    with file_lock():
        return _verify_log_unlocked()


if __name__ == "__main__":
    migration = migrate_legacy_log()

    print("Decision Log Migration")
    print("----------------------")
    print(f"Success: {migration['success']}")
    print(f"Migrated: {migration['migrated']}")
    print(migration["message"])

    if migration.get("backup_path"):
        print(f"Backup: {migration['backup_path']}")

    result = verify_log()

    print()
    print("Decision Log Verification")
    print("-------------------------")
    print(f"Valid: {result['valid']}")
    print(f"Total Records: {result['total_records']}")
    print(f"Message: {result['message']}")
