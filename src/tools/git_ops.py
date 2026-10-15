"""Commit and push inside one agent sandbox. Push stays behind human approval."""

from __future__ import annotations

import shutil
import subprocess

from src.tools.context import ToolContext


def _run_git(ctx: ToolContext, *args: str) -> str:
    executable = shutil.which("git")
    if not executable:
        return "git is not installed on this machine."
    completed = subprocess.run(
        [executable, *args],
        cwd=ctx.workspace.agent_root(ctx.agent_id),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return output or f"git exited with status {completed.returncode}."


def git_commit(ctx: ToolContext, message: str) -> str:
    if not message.strip():
        return "A commit message is required."
    init_output = _run_git(ctx, "init")
    if "not installed" in init_output:
        return init_output
    _run_git(ctx, "add", "-A")
    committed = _run_git(
        ctx,
        "-c",
        "user.email=agent@example.com",
        "-c",
        "user.name=Sandbox Agent",
        "commit",
        "-m",
        message.strip(),
    )
    return f"{init_output}\n{committed}".strip()


def git_push(ctx: ToolContext, remote: str = "origin", branch: str = "main") -> str:
    return _run_git(ctx, "push", remote, branch)
