"""Deterministic stand-in for DeepSeek / HKGAI.

The mock follows the same tool protocol as the live client, so the orchestrator,
sandboxes, and memory path can be exercised before course API keys exist.
"""

from __future__ import annotations

import json
import re
import uuid

from src.llm.client import LLMResponse, ToolCall


def _tool(name: str, arguments: dict) -> LLMResponse:
    return LLMResponse(
        content="",
        tool_calls=[
            ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=arguments)
        ],
    )


def _text(content: str) -> LLMResponse:
    return LLMResponse(content=content)


def _tool_history(messages: list[dict]) -> list[tuple[str, str, dict]]:
    names_by_id: dict[str, str] = {}
    args_by_id: dict[str, dict] = {}
    history: list[tuple[str, str, dict]] = []
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                arguments = function.get("arguments") or {}
                if isinstance(arguments, str):
                    arguments = json.loads(arguments or "{}")
                names_by_id[call["id"]] = function.get("name", "")
                args_by_id[call["id"]] = arguments
        if message.get("role") == "tool":
            call_id = message.get("tool_call_id", "")
            history.append(
                (
                    names_by_id.get(call_id, ""),
                    message.get("content", ""),
                    args_by_id.get(call_id, {}),
                )
            )
    return history


def _called(messages: list[dict], name: str) -> bool:
    return any(item[0] == name for item in _tool_history(messages))


def _last_output(messages: list[dict], name: str) -> str:
    found = ""
    for tool_name, content, _arguments in _tool_history(messages):
        if tool_name == name:
            found = content
    return found


def _last_user(messages: list[dict]) -> str:
    users = [message.get("content", "") for message in messages if message.get("role") == "user"]
    return users[-1] if users else ""


def _assignment(messages: list[dict]) -> str:
    text = _last_user(messages)
    if text.startswith("Assignment:\n"):
        body = text[len("Assignment:\n") :]
        marker = "\n\nPast lessons:"
        if marker in body:
            body = body.split(marker, 1)[0]
        return body.strip()
    return text.strip()


def _role(messages: list[dict]) -> str:
    system = ""
    for message in messages:
        if message.get("role") == "system":
            system = message.get("content", "")
            break
    for agent_id in ("coordinator", "researcher", "coder", "reviewer"):
        if f"Role: {agent_id}" in system:
            return agent_id
    return "coordinator"


def is_ambiguous(goal: str) -> bool:
    text = goal.strip().lower()
    words = re.findall(r"[a-z0-9']+", text)
    if len(words) < 5:
        return True
    vague = ("do something", "help me", "anything", "whatever", "fix it", "make it better")
    return any(phrase in text for phrase in vague)


def needs_code(goal: str) -> bool:
    text = goal.lower()
    markers = ("python", "script", "code", "fibonacci", "calculate", "compute", "program")
    return any(marker in text for marker in markers)


def effective_goal(messages: list[dict]) -> str:
    goal = _assignment(messages)
    for name, content, _arguments in _tool_history(messages):
        if name == "ask_human" and content.strip():
            goal = f"{goal}\nHuman clarification: {content.strip()}"
    return goal


def _notes(goal: str, search_text: str) -> str:
    return (
        "# Research notes\n\n"
        "## Task\n\n"
        f"{goal}\n\n"
        "## Search\n\n"
        f"{search_text}\n"
    )


def _python_source(goal: str) -> tuple[str, str]:
    lowered = goal.lower()
    if "fibonacci" in lowered:
        match = re.search(r"first\s+(\d+)", lowered)
        count = int(match.group(1)) if match else 15
        source = "\n".join(
            [
                "from pathlib import Path",
                "",
                "def fibonacci(count):",
                "    numbers = []",
                "    first, second = 0, 1",
                "    for _ in range(count):",
                "        numbers.append(first)",
                "        first, second = second, first + second",
                "    return numbers",
                "",
                f"numbers = fibonacci({count})",
                "lines = [",
                '    "# Fibonacci",',
                '    "",',
                '    "| Index | Value |",',
                '    "| --- | --- |",',
                "]",
                "for index, value in enumerate(numbers):",
                '    lines.append(f"| {index} | {value} |")',
                'Path("RESULT.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")',
                'print("Wrote RESULT.md")',
                'print(",".join(str(value) for value in numbers))',
                "",
            ]
        )
        return "fibonacci.py", source
    if "utc" in lowered or "date" in lowered:
        source = "\n".join(
            [
                "from datetime import datetime, timezone",
                "from pathlib import Path",
                "",
                'today = datetime.now(timezone.utc).strftime("%Y-%m-%d")',
                'Path("output.txt").write_text(today + "\\n", encoding="utf-8")',
                'Path("RESULT.md").write_text("# Date\\n\\nUTC date: " + today + "\\n", encoding="utf-8")',
                'print("Wrote output.txt")',
                "",
            ]
        )
        return "date_report.py", source
    quoted = json.dumps(goal)
    source = "\n".join(
        [
            "from pathlib import Path",
            "",
            f"goal = {quoted}",
            'Path("RESULT.md").write_text(',
            '    "# Result\\n\\n" + goal + "\\n\\nGenerated by the coder sandbox.\\n",',
            '    encoding="utf-8",',
            ")",
            'print("Wrote RESULT.md")',
            "",
        ]
    )
    return "task.py", source


def _written_script(messages: list[dict]) -> str:
    for _name, _content, arguments in _tool_history(messages):
        path = str(arguments.get("path", ""))
        if path.endswith(".py"):
            return path
    return "task.py"


def _handoff_names(listing: str) -> list[str]:
    return [
        line.strip()
        for line in listing.splitlines()
        if line.strip() and line.strip() != "(empty)"
    ]


def _choose_handoff(names: list[str]) -> str | None:
    for preferred in ("RESULT.md", "notes.md", "output.txt"):
        if preferred in names:
            return preferred
    return names[0] if names else None


class MockLLM:
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        role = _role(messages)
        if role == "coordinator":
            return self._coordinator(messages)
        if role == "researcher":
            return self._researcher(messages)
        if role == "coder":
            return self._coder(messages)
        return self._reviewer(messages)

    def _coordinator(self, messages: list[dict]) -> LLMResponse:
        goal = effective_goal(messages)
        if not _called(messages, "ask_human") and is_ambiguous(_assignment(messages)):
            return _tool(
                "ask_human",
                {
                    "question": (
                        "The goal is too vague to delegate. "
                        "What should the team produce, and which plain-text format should it use?"
                    )
                },
            )
        if not _called(messages, "submit_plan"):
            return _tool(
                "submit_plan",
                {
                    "subtasks": [
                        {
                            "id": "research",
                            "title": "Gather notes",
                            "description": goal,
                            "owner": "researcher",
                            "depends_on": [],
                        },
                        {
                            "id": "review",
                            "title": "Review deliverables",
                            "description": (
                                "Read the handoff folder, write review.md with PASS or FAIL, "
                                "and publish it. Do not push to GitHub."
                            ),
                            "owner": "reviewer",
                            "depends_on": ["research"],
                        },
                    ]
                },
            )
        return _text("Plan submitted. Specialists can start, and the coder is delegated only if code is required.")

    def _researcher(self, messages: list[dict]) -> LLMResponse:
        goal = _assignment(messages)
        if not _called(messages, "search"):
            return _tool("search", {"query": goal[:240]})
        if not _called(messages, "write_file"):
            return _tool(
                "write_file",
                {"path": "notes.md", "content": _notes(goal, _last_output(messages, "search"))},
            )
        if not _called(messages, "publish_handoff"):
            return _tool("publish_handoff", {"path": "notes.md"})
        if needs_code(goal) and not _called(messages, "delegate_task"):
            return _tool(
                "delegate_task",
                {
                    "owner": "coder",
                    "title": "Implement the requested script",
                    "description": goal,
                    "depends_on": ["research"],
                },
            )
        return _text("Research notes are saved in notes.md and copied to the handoff folder.")

    def _coder(self, messages: list[dict]) -> LLMResponse:
        goal = _assignment(messages)
        if not any(str(arguments.get("path", "")).endswith(".py") for _n, _c, arguments in _tool_history(messages)):
            filename, source = _python_source(goal)
            return _tool("write_file", {"path": filename, "content": source})
        if not _called(messages, "run_python"):
            return _tool("run_python", {"script": _written_script(messages)})
        run_output = _last_output(messages, "run_python")
        if "exit=0" not in run_output:
            return _text(f"FAILED: the Python script did not exit 0.\n{run_output}")
        if not _called(messages, "publish_handoff"):
            return _tool("publish_handoff", {"path": "RESULT.md"})
        return _text("Script finished and RESULT.md was published to the handoff folder.")

    def _reviewer(self, messages: list[dict]) -> LLMResponse:
        if not _called(messages, "list_handoff"):
            return _tool("list_handoff", {})
        names = _handoff_names(_last_output(messages, "list_handoff"))
        chosen = _choose_handoff(names)
        if chosen and not _called(messages, "read_handoff"):
            return _tool("read_handoff", {"name": chosen})
        if not _called(messages, "write_file"):
            if chosen:
                content = (
                    "# Review\n\n"
                    f"Source: {chosen}\n\n"
                    "Verdict: PASS\n\n"
                    "The handoff file is non-empty and uses a plain-text format.\n"
                )
            else:
                content = (
                    "# Review\n\n"
                    "Verdict: FAIL\n\n"
                    "The handoff folder had no deliverable to review.\n"
                )
            return _tool("write_file", {"path": "review.md", "content": content})
        if not _called(messages, "publish_handoff"):
            return _tool("publish_handoff", {"path": "review.md"})
        verdict = "PASS" if chosen else "FAIL"
        return _text(f"Review complete: {verdict}.")
