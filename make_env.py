import os
import secrets
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"
KEYS = ["UW_API_KEY", "UW_MCP_TOKEN", "UW_ARTIFACT_KEY"]


def main():
    if ENV_PATH.exists():
        print(".env already exists and was not changed.")
        return
    lines = [f"{key}={secrets.token_urlsafe(32)}" for key in KEYS]
    fd = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"Created {ENV_PATH} with new random secrets.")


if __name__ == "__main__":
    main()
