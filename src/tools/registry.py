"""Tool schemas, role permissions, and the single execution gate."""

from __future__ import annotations

import json

from src.config import CRITICAL_TOOLS, MAX_SPAWNED_TASKS
from src.orchestrator.delegator import make_subtask
from src.orchestrator.hitl import approved
from src.orchestrator.planner import fallback_plan
from src.tools.code_exec import run_python
from src.tools.context import ToolContext
from src.tools.files import (
    delete_file,
    list_files,
    list_handoff,
    publish_handoff,
    read_file,
    read_handoff,
    update_file,
    write_file,
)
from src.tools.git_ops import git_commit, git_push
from src.tools.search import search


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


SCHEMAS = {
    "search": _schema(
        "search",
        "Search the public web and return a short text extract.",
        {"query": _string("Search query.")},
        ["query"],
    ),
    "write_file": _schema(
        "write_file",
        "Create or replace a .md, .txt, or (coder only) .py file inside this agent's sandbox.",
        {"path": _string("Relative path."), "content": _string("Full file contents.")},
        ["path", "content"],
    ),
    "read_file": _schema(
        "read_file",
        "Read a file from this agent's sandbox.",
        {"path": _string("Relative path.")},
        ["path"],
    ),
    "update_file": _schema(
        "update_file",
        "Replace the first exact occurrence of text in a sandbox file.",
        {
            "path": _string("Relative path."),
            "old": _string("Exact text to replace."),
            "new": _string("Replacement text."),
        },
        ["path", "old", "new"],
    ),
    "delete_file": _schema(
        "delete_file",
        "Delete a file in this agent's sandbox. Requires human permission.",
        {"path": _string("Relative path.")},
        ["path"],
    ),
    "list_files": _schema(
        "list_files",
        "List files in this agent's sandbox.",
        {},
        [],
    ),
    "publish_handoff": _schema(
        "publish_handoff",
        "Copy a .md or .txt file from this sandbox into the shared handoff folder.",
        {"path": _string("Relative path of a .md or .txt file.")},
        ["path"],
    ),
    "list_handoff": _schema(
        "list_handoff",
        "List file names in the shared handoff folder.",
        {},
        [],
    ),
    "read_handoff": _schema(
        "read_handoff",
        "Read one file from the shared handoff folder by its file name.",
        {"name": _string("File name, such as RESULT.md.")},
        ["name"],
    ),
    "run_python": _schema(
        "run_python",
        "Execute a Python script that already exists in this agent's sandbox.",
        {"script": _string("Relative .py path.")},
        ["script"],
    ),
    "git_commit": _schema(
        "git_commit",
        "Commit the current sandbox contents. Does not push.",
        {"message": _string("Commit message.")},
        ["message"],
    ),
    "git_push": _schema(
        "git_push",
        "Push the sandbox repository. Requires human permission.",
        {
            "remote": _string("Remote name. Defaults to origin."),
            "branch": _string("Branch name. Defaults to main."),
        },
        [],
    ),
    "delegate_task": _schema(
        "delegate_task",
        "Assign a new subtask to researcher, coder, or reviewer.",
        {
            "owner": _string("researcher, coder, or reviewer."),
            "title": _string("Short title."),
            "description": _string("Full instructions for the assignee."),
            "depends_on": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subtask ids that must finish first.",
            },
        },
        ["owner", "title", "description"],
    ),
    "ask_human": _schema(
        "ask_human",
        "Pause and ask the human for clarification.",
        {"question": _string("The question to ask.")},
        ["question"],
    ),
    "submit_plan": _schema(
        "submit_plan",
        "Submit the task plan. Each subtask needs id, title, description, owner, and depends_on.",
        {
            "subtasks": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Ordered subtasks for the specialists.",
            }
        },
        ["subtasks"],
    ),
}

ROLE_TOOLS = {
    "coordinator": ["submit_plan", "ask_human", "delegate_task"],
    "researcher": [
        "search",
        "read_file",
        "write_file",
        "update_file",
        "list_files",
        "publish_handoff",
        "read_handoff",
        "list_handoff",
        "delegate_task",
        "ask_human",
    ],
    "coder": [
        "read_file",
        "write_file",
        "update_file",
        "delete_file",
        "list_files",
        "run_python",
        "publish_handoff",
        "read_handoff",
        "list_handoff",
        "delegate_task",
        "ask_human",
    ],
    "reviewer": [
        "read_file",
        "write_file",
        "list_files",
        "read_handoff",
        "list_handoff",
        "publish_handoff",
        "git_commit",
        "git_push",
        "ask_human",
    ],
}

FUNCTIONS = {
    "search": search,
    "write_file": write_file,
    "read_file": read_file,
    "update_file": update_file,
    "delete_file": delete_file,
    "list_files": list_files,
    "publish_handoff": publish_handoff,
    "list_handoff": list_handoff,
    "read_handoff": read_handoff,
    "run_python": run_python,
    "git_commit": git_commit,
    "git_push": git_push,
    "delegate_task": None,
    "ask_human": None,
    "submit_plan": None,
}


def tool_schemas(agent_id: str) -> list[dict]:
    return [SCHEMAS[name] for name in ROLE_TOOLS[agent_id]]


def truncate(text: str, limit: int = 350) -> str:
    flattened = text.replace("\r", "")
    if len(flattened) <= limit:
        return flattened
    return flattened[:limit] + "..."


def _ask(ctx: ToolContext, question: str, kind: str) -> str:
    ctx.chat.post(ctx.conversation_id, ctx.agent_id, question, kind="hitl_request")
    answer = ctx.human.ask(ctx.agent_id, question, kind)
    ctx.chat.post(ctx.conversation_id, "human", answer, kind="hitl_response")
    return answer


def _submit_plan(ctx: ToolContext, subtasks: list | str) -> str:
    if isinstance(subtasks, str):
        subtasks = json.loads(subtasks)
    if not isinstance(subtasks, list) or not subtasks:
        ctx.plan = fallback_plan("No goal was provided.")
        return "Plan was empty. A default plan was recorded."
    recorded = []
    for raw in subtasks:
        if not isinstance(raw, dict):
            return "Each subtask must be an object."
        owner = str(raw.get("owner", "")).strip()
        if owner not in {"researcher", "coder", "reviewer"}:
            return f"Invalid owner '{owner}'."
        task = make_subtask(
            owner=owner,
            title=str(raw.get("title", owner)),
            description=str(raw.get("description", "")),
            depends_on=_as_list(raw.get("depends_on")),
            existing_ids={item.id for item in recorded},
        )
        task.id = str(raw.get("id") or task.id)
        recorded.append(task)
    ctx.plan = recorded
    return f"Recorded {len(recorded)} subtasks."


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item) for item in value]


def _delegate(
    ctx: ToolContext,
    owner: str,
    title: str,
    description: str,
    depends_on: list[str] | None = None,
) -> str:
    if len(ctx.spawned) >= MAX_SPAWNED_TASKS:
        return "Delegation limit reached."
    try:
        task = make_subtask(owner, title, description, _as_list(depends_on))
    except ValueError as exc:
        return str(exc)
    ctx.spawned.append(task)
    return f"Delegated {task.id} to {owner}: {task.title}"


def execute(ctx: ToolContext, name: str, arguments: dict | None) -> str:
    arguments = dict(arguments or {})
    if name not in SCHEMAS:
        return f"Unknown tool '{name}'."
    if name not in ctx.allowed:
        return f"Tool '{name}' is not available to {ctx.agent_id}."

    if name in CRITICAL_TOOLS:
        question = f"Allow {name} with arguments {json.dumps(arguments, sort_keys=True)}?"
        answer = _ask(ctx, question, "permission")
        if not approved(answer):
            denied = f"Human denied {name}."
            ctx.chat.post(ctx.conversation_id, ctx.agent_id, denied, kind="tool")
            return denied

    try:
        if name == "ask_human":
            answer = _ask(ctx, str(arguments.get("question", "Please clarify the task.")), "clarification")
            ctx.clarifications.append(answer)
            return answer
        if name == "submit_plan":
            result = _submit_plan(ctx, arguments.get("subtasks", []))
        elif name == "delegate_task":
            result = _delegate(
                ctx,
                owner=str(arguments.get("owner", "")),
                title=str(arguments.get("title", "")),
                description=str(arguments.get("description", "")),
                depends_on=arguments.get("depends_on"),
            )
        else:
            result = FUNCTIONS[name](ctx, **arguments)
    except TypeError as exc:
        result = f"Bad arguments for {name}: {exc}"
    except Exception as exc:
        result = f"Tool {name} failed: {exc}"

    ctx.chat.post(ctx.conversation_id, ctx.agent_id, f"{name}: {truncate(str(result))}", kind="tool")
    return str(result)
