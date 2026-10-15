"""Sandbox and document-format checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.chat.service import ChatService
from src.orchestrator.hitl import ScriptedHuman
from src.sandbox.workspace import Workspace
from src.tools.context import ToolContext
from src.tools.files import read_file, write_file


class SandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.workspace = Workspace(self.root)
        self.workspace.ensure()
        self.chat = ChatService(self.workspace.chats, echo=False)
        self.conversation = self.chat.open("dm", ["human", "coder"])
        self.context = ToolContext(
            agent_id="coder",
            conversation_id=self.conversation.id,
            workspace=self.workspace,
            human=ScriptedHuman(),
            chat=self.chat,
            offline=True,
            allowed={"write_file", "read_file"},
        )

    def test_rejects_parent_path(self) -> None:
        with self.assertRaises(PermissionError):
            self.workspace.resolve_agent_path("coder", "../researcher/secret.md")

    def test_cannot_read_another_agent(self) -> None:
        secret = self.workspace.agent_root("researcher") / "secret.md"
        secret.write_text("hidden", encoding="utf-8")
        with self.assertRaises(PermissionError):
            read_file(self.context, "../researcher/secret.md")

    def test_rejects_pdf(self) -> None:
        with self.assertRaises(ValueError):
            write_file(self.context, "report.pdf", "not allowed")

    def test_writes_markdown(self) -> None:
        message = write_file(self.context, "notes.md", "# Hello\n")
        self.assertIn("Wrote notes.md", message)
        self.assertEqual(
            (self.workspace.agent_root("coder") / "notes.md").read_text(encoding="utf-8"),
            "# Hello\n",
        )


if __name__ == "__main__":
    unittest.main()
