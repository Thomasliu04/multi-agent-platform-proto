"""Run the practice set and score file-based success criteria."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.metrics.report import render_report
from src.orchestrator.hitl import ScriptedHuman
from src.orchestrator.runner import Platform


def load_tasks(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("The task file must be a JSON list.")
    return payload


def check_success(root: Path, spec: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    for relative in spec.get("file_exists") or []:
        path = root / relative
        if path.is_file():
            notes.append(f"found {relative}")
        else:
            ok = False
            notes.append(f"missing {relative}")
    for relative, needle in (spec.get("file_contains") or {}).items():
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if needle in text:
            notes.append(f"{relative} contains {needle!r}")
        else:
            ok = False
            notes.append(f"{relative} does not contain {needle!r}")
    for relative, pattern in (spec.get("file_matches") or {}).items():
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if re.search(pattern, text.strip()):
            notes.append(f"{relative} matches {pattern}")
        else:
            ok = False
            notes.append(f"{relative} does not match {pattern}")
    return ok, notes


def run_suite(
    root: Path,
    tasks: list[dict],
    offline: bool = True,
    echo: bool = False,
    provider: str | None = None,
) -> tuple[str, list]:
    platform = Platform(root=root, offline=offline, echo=echo, provider=provider)
    for task in tasks:
        platform.human = ScriptedHuman(task.get("human_responses"))
        if task.get("mode") == "dm":
            record = platform.run_dm(task["agent"], task["goal"], task_id=task["id"])
        else:
            record = platform.run_group(task["goal"], task_id=task["id"])
        if task.get("success"):
            met, notes = check_success(root, task["success"])
            record.criteria_met = met
            record.criteria_notes = notes
    report = render_report(platform.metrics.runs)
    destination = platform.workspace.results / "report.md"
    destination.write_text(report, encoding="utf-8")
    return report, platform.metrics.runs
