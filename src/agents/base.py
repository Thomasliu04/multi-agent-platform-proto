"""Shared think-act-observe loop used by every role."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.agents.prompts import PROMPTS
from src.chat.models import SubTask
from src.chat.service import ChatService
from src.config import MAX_AGENT_STEPS
from src.memory.store import MemoryStore
from src.orchestrator.hitl import HumanInterface
from src.sandbox.workspace import Workspace
from src.tools.context import ToolContext
from src.tools.registry import execute, tool_schemas


@dataclass
class AgentResult:
    ok: bool
    text: str
    plan: list[SubTask] = field(default_factory=list)
    spawned: list[SubTask] = field(default_factory=list)
    clarifications: list[str] = field(default_factory=list)


class AgentRuntime:
    def __init__(
        self,
        llm,
        workspace: Workspace,
        memory: MemoryStore,
        chat: ChatService,
        human: HumanInterface,
        offline: bool = False,
    ) -> None:
        self.llm = llm
        self.workspace = workspace
        self.memory = memory
        self.chat = chat
        self.human = human
        self.offline = offline

    def run(self, agent_id: str, assignment: str, conversation_id: str) -> AgentResult:
        lessons = self.memory.retrieve(agent_id, assignment)
        if lessons:
            self.chat.post(
                conversation_id,
                agent_id,
                f"Recalled {len(lessons)} past lesson(s).",
                kind="memory",
            )
        messages = [
            {"role": "system", "content": PROMPTS[agent_id]},
            {
                "role": "user",
                "content": (
                    f"Assignment:\n{assignment}\n\n"
                    f"Past lessons:\n{self.memory.format_lessons(lessons)}"
                ),
            },
        ]
        context = ToolContext(
            agent_id=agent_id,
            conversation_id=conversation_id,
            workspace=self.workspace,
            human=self.human,
            chat=self.chat,
            offline=self.offline,
            allowed=set(tool["name"] for tool in tool_schemas(agent_id)),
        )
        for _step in range(MAX_AGENT_STEPS):
            try:
                response = self.llm.complete(messages, tool_schemas(agent_id))
            except Exception as exc:
                text = f"FAILED: model call failed: {exc}"
                self.chat.post(conversation_id, agent_id, text)
                return self._result(context, ok=False, text=text)
            if not response.tool_calls:
                text = response.content.strip() or "No response."
                self.chat.post(conversation_id, agent_id, text)
                return self._result(context, ok=not text.startswith("FAILED"), text=text)
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for call in response.tool_calls
                    ],
                }
            )
            for call in response.tool_calls:
                output = execute(context, call.name, call.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                )
        text = "FAILED: exceeded the maximum number of tool steps."
        self.chat.post(conversation_id, agent_id, text)
        return self._result(context, ok=False, text=text)

    @staticmethod
    def _result(context: ToolContext, ok: bool, text: str) -> AgentResult:
        return AgentResult(
            ok=ok,
            text=text,
            plan=list(context.plan),
            spawned=list(context.spawned),
            clarifications=list(context.clarifications),
        )
