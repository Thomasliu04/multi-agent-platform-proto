"""Human approval gates for destructive tools."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.chat.service import ChatService
from src.orchestrator.hitl import ScriptedHuman
from src.sandbox.workspace import Workspace
from src.tools.context import ToolContext
from src.tools.registry import execute


class HitlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.workspace = Workspace(self.root)
        self.workspace.ensure()
        self.chat = ChatService(self.workspace.chats, echo=False)
        self.conversation = self.chat.open("dm", ["human", "coder"])
        self.note = self.workspace.agent_root("coder") / "note.txt"
        self.note.write_text("keep me", encoding="utf-8")

    def _context(self, human: ScriptedHuman) -> ToolContext:
        return ToolContext(
            agent_id="coder",
            conversation_id=self.conversation.id,
            workspace=self.workspace,
            human=human,
            chat=self.chat,
            offline=True,
            allowed={"delete_file", "git_push"},
        )

    def test_delete_is_blocked_until_approved(self) -> None:
        denied = execute(self._context(ScriptedHuman(["no"])), "delete_file", {"path": "note.txt"})
        self.assertIn("denied", denied.lower())
        self.assertTrue(self.note.is_file())

        allowed = execute(self._context(ScriptedHuman(["yes"])), "delete_file", {"path": "note.txt"})
        self.assertIn("Deleted", allowed)
        self.assertFalse(self.note.exists())

    def test_push_is_blocked_without_approval(self) -> None:
        human = ScriptedHuman(["no"])
        result = execute(self._context(human), "git_push", {"remote": "origin", "branch": "main"})
        self.assertIn("denied", result.lower())
        self.assertEqual(human.log[0]["kind"], "permission")


if __name__ == "__main__":
    unittest.main()
