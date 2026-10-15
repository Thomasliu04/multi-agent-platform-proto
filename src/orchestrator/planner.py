"""Turn a goal into the default research-then-review plan."""

from __future__ import annotations

from src.chat.models import SubTask


def fallback_plan(goal: str) -> list[SubTask]:
    """Used when the coordinator does not return a structured plan."""
    return [
        SubTask(
            id="research",
            title="Gather notes",
            description=goal,
            owner="researcher",
        ),
        SubTask(
            id="review",
            title="Review deliverables",
            description=(
                "Read the handoff folder, write review.md with a PASS or FAIL verdict, "
                "and publish the review. Do not push to GitHub."
            ),
            owner="reviewer",
            depends_on=["research"],
        ),
    ]


def format_plan(subtasks: list[SubTask]) -> str:
    lines = ["Plan:"]
    for task in subtasks:
        deps = f" after {', '.join(task.depends_on)}" if task.depends_on else ""
        lines.append(f"- {task.id} -> {task.owner}: {task.title}{deps}")
    return "\n".join(lines)
