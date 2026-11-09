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
PROTECTED_FIELDS = {"gender", "age_group", "default_flag"}
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def valid_applicant_id(value):
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def strip_protected(record):
    return {k: v for k, v in record.items() if k not in PROTECTED_FIELDS}


def sanitize_csv_value(value):
    if isinstance(value, str):
        cleaned = _CONTROL_CHARS.sub("", value).replace("\r", " ").replace("\n", " ")
        if cleaned and cleaned[0] in ("=", "+", "-", "@", "\t"):
            return "'" + cleaned
        return cleaned
    return value


def safe_text(value, limit):
    if not isinstance(value, str):
        return ""
    return _CONTROL_CHARS.sub("", value).strip()[:limit]


def constant_time_equal(supplied, expected):
    return hmac.compare_digest(str(supplied).encode("utf-8"), str(expected).encode("utf-8"))


def _signature_path(path):
    return path + ".sig"


def _compute_signature(path):
    key = config.secret("UW_ARTIFACT_KEY").encode("utf-8")
    digest = hmac.new(key, digestmod=hashlib.sha256)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_signature(path):
    sig_path = _signature_path(path)
    fd = os.open(sig_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_compute_signature(path))


def verify_signature(path):
    sig_path = _signature_path(path)
    if not os.path.exists(path):
        raise FileNotFoundError("Model artefacts not found. Run 'python train_model.py' first.")
    if not os.path.exists(sig_path):
        raise RuntimeError("Artefact signature missing. Retrain with 'python train_model.py'.")
    with open(sig_path, "r", encoding="utf-8") as handle:
        stored = handle.read().strip()
    if not hmac.compare_digest(stored, _compute_signature(path)):
        raise RuntimeError("Artefact signature mismatch: file was modified or signed with a different key.")


def load_verified_artifacts(path):
    verify_signature(path)
    return joblib.load(path)


class RateLimiter:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key):
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if len(self._hits) > 10000:
                for stale in [k for k, v in self._hits.items() if not v]:
                    del self._hits[stale]
            return True
