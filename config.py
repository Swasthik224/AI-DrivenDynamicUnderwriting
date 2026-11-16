import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent


def _load_env_file():
    path = BASE_DIR / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def secret(name):
    value = os.environ.get(name, "")
    if len(value) < 24 or value.lower().startswith("change-me"):
        raise RuntimeError(
            f"{name} is missing or too weak. Run 'python make_env.py' to generate strong secrets."
        )
    return value


def _validated_ollama_url():
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise RuntimeError("OLLAMA_URL must point to a local Ollama instance (http://127.0.0.1 or http://localhost).")
    return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 11434}"


API_HOST = "127.0.0.1"
API_PORT = _int("UW_API_PORT", 8000)
MCP_HOST = "127.0.0.1"
MCP_PORT = _int("UW_MCP_PORT", 8001)
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
DASH_HOST = "127.0.0.1"
DASH_PORT = _int("UW_DASH_PORT", 5000)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS", f"http://127.0.0.1:{DASH_PORT},http://localhost:{DASH_PORT}"
    ).split(",")
    if o.strip() and o.strip() != "*"
]
ENABLE_DOCS = os.environ.get("UW_ENABLE_DOCS", "0") == "1"
RATE_LIMIT_PER_MIN = _int("UW_RATE_LIMIT_PER_MIN", 60)
MAX_BODY_BYTES = _int("UW_MAX_BODY_BYTES", 32768)
OLLAMA_URL = _validated_ollama_url()

ARTIFACT_PATH = str(BASE_DIR / "underwriting_artifacts.pkl")
DATASET_PATH = str(BASE_DIR / "underwriting_dataset.csv")
HOME_CREDIT_DIR = BASE_DIR / "home-credit-default-risk"
HOME_CREDIT_TRAIN_PATH = str(HOME_CREDIT_DIR / "application_train.csv")
HOME_CREDIT_TEST_PATH = str(HOME_CREDIT_DIR / "application_test.csv")