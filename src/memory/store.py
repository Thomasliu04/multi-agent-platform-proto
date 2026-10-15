"""JSON lesson log, one file per agent."""

from __future__ import annotations

import json
from pathlib import Path

from src.chat.models import utc_now
from src.memory.retrieve import rank_lessons


class MemoryStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path_for(self, agent_id: str) -> Path:
        return self.directory / f"{agent_id}.json"

    def load(self, agent_id: str) -> list[dict]:
        path = self.path_for(agent_id)
        if not path.is_file():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        return payload

    def append(self, agent_id: str, entry: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        lessons = self.load(agent_id)
        stored = dict(entry)
        stored.setdefault("timestamp", utc_now())
        lessons.append(stored)
        self.path_for(agent_id).write_text(
            json.dumps(lessons, indent=2),
            encoding="utf-8",
        )

    def retrieve(self, agent_id: str, query: str, limit: int = 3) -> list[dict]:
        return rank_lessons(self.load(agent_id), query, limit)

    def format_lessons(self, lessons: list[dict]) -> str:
        if not lessons:
            return "None yet."
        lines = []
        for lesson in lessons:
            outcome = lesson.get("outcome", "unknown")
            text = lesson.get("lesson", "")
            lines.append(f"- ({outcome}) {text}")
        return "\n".join(lines)
