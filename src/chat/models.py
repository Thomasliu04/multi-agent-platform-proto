"""Shared records for chats, tasks, and runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Message:
    role: str
    sender: str
    content: str
    conversation_id: str
    kind: str = "chat"
    timestamp: str = field(default_factory=utc_now)


@dataclass
class Conversation:
    id: str
    kind: str
    participants: list[str]
    messages: list[Message] = field(default_factory=list)


@dataclass
class SubTask:
    id: str
    title: str
    description: str
    owner: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    result: str = ""


@dataclass
class RunRecord:
    task_id: str
    goal: str
    mode: str
    started_at: str
    ended_at: str
    seconds: float
    subtasks: list[dict]
    fatal: bool
    conversation_id: str
    transcript: list[str] = field(default_factory=list)
    criteria_met: bool | None = None
    criteria_notes: list[str] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        if not self.subtasks:
            return 0.0
        done = sum(1 for item in self.subtasks if item["status"] == "done")
        return done / len(self.subtasks)

    @property
    def success(self) -> bool:
        return bool(self.subtasks) and not self.fatal and all(
            item["status"] == "done" for item in self.subtasks
        )
