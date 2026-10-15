"""Runtime constants for the prototype."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

AGENT_IDS = ("coordinator", "researcher", "coder", "reviewer")
SPECIALIST_IDS = ("researcher", "coder", "reviewer")
DOCUMENT_SUFFIXES = {".md", ".txt"}
CODE_SUFFIXES = {".py"}

CRITICAL_TOOLS = frozenset({"delete_file", "git_push"})
MAX_AGENT_STEPS = 10
MAX_SPAWNED_TASKS = 5
CODE_TIMEOUT_SEC = 15
SEARCH_TIMEOUT_SEC = 8


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs without overriding variables already in the environment."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
