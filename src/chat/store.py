"""JSON persistence for chat transcripts."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.chat.models import Conversation, Message


def save_conversation(directory: Path, conversation: Conversation) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{conversation.id}.json"
    path.write_text(json.dumps(asdict(conversation), indent=2), encoding="utf-8")
    return path


def load_conversation(path: Path) -> Conversation:
    payload = json.loads(path.read_text(encoding="utf-8"))
    messages = [Message(**item) for item in payload.pop("messages")]
    return Conversation(messages=messages, **payload)
