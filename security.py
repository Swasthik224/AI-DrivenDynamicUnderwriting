import hashlib
import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque

import joblib

import config

APPLICANT_ID_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"
_ID_RE = re.compile(APPLICANT_ID_PATTERN)

PROTECTED_FIELDS = {
    "gender",
    "age_group",
    "default_flag",
    "CODE_GENDER",
    "DAYS_BIRTH",
    "NAME_FAMILY_STATUS",
    "TARGET",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def valid_applicant_id(value):
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def strip_protected(record):
    if not isinstance(record, dict):
        return {}
    return {key: value for key, value in record.items() if key not in PROTECTED_FIELDS}


def sanitize_csv_value(value):
    if not isinstance(value, str):
        return value

    cleaned = _CONTROL_CHARS.sub("", value)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")

    if cleaned.lstrip().startswith(("=", "+", "-", "@", "\t")):
        return "'" + cleaned

    return cleaned


def safe_text(value, limit):
    if not isinstance(value, str):
        return ""
    return _CONTROL_CHARS.sub("", value).strip()[:limit]


def constant_time_equal(supplied, expected):
    if supplied is None or expected is None:
        return False

    return hmac.compare_digest(
        str(supplied).encode("utf-8"),
        str(expected).encode("utf-8")
    )


def _signature_path(path):
    return path + ".sig"


def _compute_signature(path):
    key = config.secret("UW_ARTIFACT_KEY").encode("utf-8")

    if not key:
        raise RuntimeError("Artifact signing key is empty.")

    digest = hmac.new(key, digestmod=hashlib.sha256)

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def write_signature(path):
    if not os.path.isfile(path):
        raise FileNotFoundError("Model artifact file not found.")

    signature = _compute_signature(path)
    sig_path = _signature_path(path)
    temporary_path = sig_path + ".tmp"

    fd = os.open(
        temporary_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(signature)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, sig_path)

        try:
            os.chmod(sig_path, 0o600)
        except OSError:
            pass

    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def verify_signature(path):
    sig_path = _signature_path(path)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            "Model artifacts not found. Run 'python train_model.py' first."
        )

    if not os.path.isfile(sig_path):
        raise RuntimeError(
            "Artifact signature missing. Retrain with 'python train_model.py'."
        )

    with open(sig_path, "r", encoding="utf-8") as handle:
        stored = handle.read().strip()

    if not re.fullmatch(r"[0-9a-fA-F]{64}", stored):
        raise RuntimeError("Artifact signature has an invalid format.")

    calculated = _compute_signature(path)

    if not hmac.compare_digest(stored.lower(), calculated.lower()):
        raise RuntimeError(
            "Artifact signature mismatch: file was modified or signed with a different key."
        )


def load_verified_artifacts(path):
    verify_signature(path)
    return joblib.load(path)


class RateLimiter:
    def __init__(self, limit, window_seconds):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("Rate limit must be a positive integer.")

        if window_seconds <= 0:
            raise ValueError("Window duration must be positive.")

        self.limit = limit
        self.window = float(window_seconds)
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key):
        now = time.monotonic()

        with self._lock:
            hits = self._hits[key]

            while hits and now - hits[0] >= self.window:
                hits.popleft()

            if len(hits) >= self.limit:
                return False

            hits.append(now)

            if len(self._hits) > 10000:
                stale_keys = []

                for stored_key, stored_hits in self._hits.items():
                    while stored_hits and now - stored_hits[0] >= self.window:
                        stored_hits.popleft()

                    if not stored_hits:
                        stale_keys.append(stored_key)

                for stale_key in stale_keys:
                    self._hits.pop(stale_key, None)

            return True