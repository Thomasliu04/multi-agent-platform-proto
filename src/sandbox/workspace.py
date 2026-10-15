"""Private agent directories plus one shared handoff folder."""

from __future__ import annotations

from pathlib import Path

from src.config import AGENT_IDS, DOCUMENT_SUFFIXES


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.agents_root = root / "workspaces"
        self.handoff = self.agents_root / "handoff"
        self.data = root / "data"
        self.chats = self.data / "chats"
        self.memory = self.data / "memory"
        self.results = root / "eval" / "results"

    def ensure(self) -> None:
        for agent_id in AGENT_IDS:
            (self.agents_root / agent_id).mkdir(parents=True, exist_ok=True)
        for directory in (self.handoff, self.chats, self.memory, self.results):
            directory.mkdir(parents=True, exist_ok=True)

    def agent_root(self, agent_id: str) -> Path:
        if agent_id not in AGENT_IDS:
            raise ValueError(f"Unknown agent '{agent_id}'.")
        return (self.agents_root / agent_id).resolve()

    def resolve_agent_path(self, agent_id: str, relative: str) -> Path:
        rel = Path(relative)
        if rel.is_absolute() or any(part == ".." for part in rel.parts):
            raise PermissionError(f"Path escapes the {agent_id} sandbox: {relative}")
        root = self.agent_root(agent_id)
        target = (root / rel).resolve()
        if target != root and root not in target.parents:
            raise PermissionError(f"Path escapes the {agent_id} sandbox: {relative}")
        return target

    def check_suffix(self, path: Path, agent_id: str) -> None:
        suffix = path.suffix.lower()
        if suffix in DOCUMENT_SUFFIXES:
            return
        if suffix == ".py" and agent_id == "coder":
            return
        allowed = sorted(DOCUMENT_SUFFIXES)
        if agent_id == "coder":
            allowed.append(".py")
        raise ValueError(
            f"Files must use {allowed}. Refusing '{path.name}'."
        )
