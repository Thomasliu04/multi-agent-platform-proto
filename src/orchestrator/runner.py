"""Group and direct-message runs."""

from __future__ import annotations

import uuid
from pathlib import Path

from src.agents.base import AgentRuntime
from src.chat.models import RunRecord, SubTask, utc_now
from src.chat.service import ChatService
from src.config import AGENT_IDS
from src.llm.client import build_llm
from src.memory.store import MemoryStore
from src.metrics.tracker import Metrics
from src.orchestrator.delegator import extend_unique, next_runnable
from src.orchestrator.hitl import HumanInterface, ScriptedHuman
from src.orchestrator.planner import fallback_plan, format_plan
from src.sandbox.workspace import Workspace


class Platform:
    def __init__(
        self,
        root: Path | str,
        llm=None,
        human: HumanInterface | None = None,
        offline: bool = True,
        echo: bool = True,
        provider: str | None = None,
    ) -> None:
        self.root = Path(root)
        self.workspace = Workspace(self.root)
        self.workspace.ensure()
        self.offline = offline
        self.echo = echo
        self.human = human or ScriptedHuman()
        self.chat = ChatService(self.workspace.chats, echo=echo)
        self.memory = MemoryStore(self.workspace.memory)
        self.llm = llm if llm is not None else build_llm(provider)
        self.agents = AgentRuntime(
            llm=self.llm,
            workspace=self.workspace,
            memory=self.memory,
            chat=self.chat,
            human=self.human,
            offline=offline,
        )
        self.metrics = Metrics(self.workspace.results)

    def run_group(self, goal: str, task_id: str | None = None) -> RunRecord:
        self.agents.human = self.human
        self.agents.offline = self.offline
        started = self.metrics.begin()
        started_at = utc_now()
        fatal = False
        conversation = self.chat.open("group", ["human", *AGENT_IDS])
        self.chat.post(conversation.id, "human", goal, kind="task")

        try:
            coordinated = self.agents.run("coordinator", goal, conversation.id)
        except Exception as exc:
            fatal = True
            coordinated = None
            self.chat.post(conversation.id, "coordinator", f"FAILED: {exc}")

        effective = goal
        plan = []
        if coordinated is not None:
            if coordinated.clarifications:
                effective = f"{goal}\nHuman clarification: {coordinated.clarifications[-1]}"
            plan = list(coordinated.plan)
            self._remember(
                "coordinator",
                goal,
                coordinated.ok and bool(plan),
                "Plan the work",
                coordinated.text,
            )
        if not plan:
            plan = fallback_plan(effective)
            self.chat.post(
                conversation.id,
                "coordinator",
                "No structured plan was returned. Using the default research and review plan.",
            )
        self.chat.post(conversation.id, "coordinator", format_plan(plan), kind="plan")
        fatal = self._execute_queue(conversation.id, plan, fatal) or fatal
        return self._record(
            task_id or conversation.id,
            goal,
            "group",
            started,
            plan,
            fatal,
            conversation.id,
            started_at,
        )

    def run_dm(self, agent_id: str, goal: str, task_id: str | None = None) -> RunRecord:
        if agent_id not in AGENT_IDS or agent_id == "coordinator":
            raise ValueError("Direct messages must target researcher, coder, or reviewer.")
        self.agents.human = self.human
        self.agents.offline = self.offline
        started = self.metrics.begin()
        started_at = utc_now()
        conversation = self.chat.open("dm", ["human", agent_id])
        self.chat.post(conversation.id, "human", goal, kind="task")
        task = SubTask(id="direct", title="Direct request", description=goal, owner=agent_id)
        fatal = self._execute_queue(conversation.id, [task], fatal=False)
        return self._record(
            task_id or f"dm-{uuid.uuid4().hex[:6]}",
            goal,
            "dm",
            started,
            [task],
            fatal,
            conversation.id,
            started_at,
        )

    def _execute_queue(self, conversation_id: str, subtasks: list[SubTask], fatal: bool) -> bool:
        for _guard in range(20):
            current = next_runnable(subtasks)
            if current is None:
                break
            current.status = "running"
            self.chat.post(
                conversation_id,
                "system",
                f"Starting {current.id} assigned to {current.owner}.",
                kind="status",
            )
            try:
                result = self.agents.run(current.owner, current.description, conversation_id)
            except Exception as exc:
                fatal = True
                current.status = "failed"
                current.result = str(exc)
                self.chat.post(conversation_id, current.owner, f"FAILED: {exc}")
                self._remember(current.owner, current.description, False, current.title, str(exc))
                continue
            current.status = "done" if result.ok else "failed"
            current.result = result.text
            extend_unique(subtasks, result.spawned)
            self._remember(current.owner, current.description, result.ok, current.title, result.text)
        else:
            fatal = True
        return fatal

    def _remember(self, agent_id: str, assignment: str, ok: bool, title: str, detail: str) -> None:
        if ok:
            lesson = f"Completed '{title}' for a similar assignment."
            outcome = "success"
        else:
            lesson = f"Failed '{title}'. Last output: {detail[:180]}"
            outcome = "failure"
        self.memory.append(
            agent_id,
            {
                "task": assignment[:500],
                "title": title,
                "outcome": outcome,
                "lesson": lesson,
            },
        )

    def _record(
        self,
        task_id: str,
        goal: str,
        mode: str,
        started: float,
        subtasks: list[SubTask],
        fatal: bool,
        conversation_id: str,
        started_at: str,
    ) -> RunRecord:
        self.chat.save(conversation_id)
        transcript = [
            f"{message.sender}: {message.content}"
            for message in self.chat.conversations[conversation_id].messages
        ]
        return self.metrics.finish(
            task_id=task_id,
            goal=goal,
            mode=mode,
            started=started,
            subtasks=[
                {
                    "id": task.id,
                    "title": task.title,
                    "owner": task.owner,
                    "status": task.status,
                    "result": task.result[:500],
                }
                for task in subtasks
            ],
            fatal=fatal,
            conversation_id=conversation_id,
            transcript=transcript,
            started_at=started_at,
        )
