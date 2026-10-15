"""Per-step state passed into tool functions."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.chat.models import SubTask
from src.chat.service import ChatService
from src.orchestrator.hitl import HumanInterface
from src.sandbox.workspace import Workspace


@dataclass
class ToolContext:
    agent_id: str
    conversation_id: str
    workspace: Workspace
    human: HumanInterface
    chat: ChatService
    offline: bool = False
    allowed: set[str] = field(default_factory=set)
    plan: list[SubTask] = field(default_factory=list)
    spawned: list[SubTask] = field(default_factory=list)
    clarifications: list[str] = field(default_factory=list)
