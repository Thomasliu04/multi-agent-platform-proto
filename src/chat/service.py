"""In-memory chat log that also writes each conversation to disk."""

from __future__ import annotations

import uuid
from pathlib import Path

from src.chat.models import Conversation, Message
from src.chat.store import save_conversation
from src.config import AGENT_IDS


class ChatService:
    def __init__(self, directory: Path, echo: bool = True) -> None:
        self.directory = directory
        self.echo = echo
        self.conversations: dict[str, Conversation] = {}

    def open(self, kind: str, participants: list[str]) -> Conversation:
        conversation = Conversation(
            id=uuid.uuid4().hex[:8],
            kind=kind,
            participants=participants,
        )
        self.conversations[conversation.id] = conversation
        return conversation

    def post(self, conversation_id: str, sender: str, content: str, kind: str = "chat") -> Message:
        conversation = self.conversations[conversation_id]
        if sender == "human":
            role = "human"
        elif sender in AGENT_IDS:
            role = "agent"
        else:
            role = "system"
        message = Message(
            role=role,
            sender=sender,
            content=content,
            conversation_id=conversation_id,
            kind=kind,
        )
        conversation.messages.append(message)
        if self.echo:
            shown = content if len(content) <= 400 else content[:400] + "..."
            print(f"[{sender}] {shown}")
        return message

    def save(self, conversation_id: str) -> Path:
        return save_conversation(self.directory, self.conversations[conversation_id])
