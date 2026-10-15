"""Run a Python file inside the calling agent's sandbox."""

from __future__ import annotations

import os
import subprocess
import sys

from src.config import CODE_TIMEOUT_SEC
from src.tools.context import ToolContext


def run_python(ctx: ToolContext, script: str) -> str:
    path = ctx.workspace.resolve_agent_path(ctx.agent_id, script)
    if path.suffix.lower() != ".py":
        return "Only .py files can be executed."
    if not path.is_file():
        return f"Script not found: {script}"
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(secret in key.upper() for secret in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
    }
    try:
        completed = subprocess.run(
            [sys.executable, path.name],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=CODE_TIMEOUT_SEC,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"exit=124\nstdout:\n\nstderr:\nTimed out after {CODE_TIMEOUT_SEC}s."
    return (
        f"exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
