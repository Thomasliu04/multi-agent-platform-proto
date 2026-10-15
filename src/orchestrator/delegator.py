"""Choose the next subtask and accept agent-to-agent assignments."""

from __future__ import annotations

from src.chat.models import SubTask
from src.config import SPECIALIST_IDS

TERMINAL = {"done", "failed", "blocked"}


def make_subtask(
    owner: str,
    title: str,
    description: str,
    depends_on: list[str] | None = None,
    existing_ids: set[str] | None = None,
) -> SubTask:
    if owner not in SPECIALIST_IDS:
        raise ValueError(f"Cannot delegate to '{owner}'.")
    taken = existing_ids or set()
    index = 1
    candidate = f"{owner}-{index}"
    while candidate in taken:
        index += 1
        candidate = f"{owner}-{index}"
    return SubTask(
        id=candidate,
        title=title.strip() or f"{owner} task",
        description=description.strip(),
        owner=owner,
        depends_on=list(depends_on or []),
    )


def extend_unique(subtasks: list[SubTask], spawned: list[SubTask]) -> list[SubTask]:
    added: list[SubTask] = []
    taken = {task.id for task in subtasks}
    for task in spawned:
        duplicate = any(
            current.owner == task.owner and current.title == task.title for current in subtasks
        )
        if duplicate:
            continue
        if task.id in taken:
            task.id = make_subtask(
                task.owner,
                task.title,
                task.description,
                task.depends_on,
                taken,
            ).id
        subtasks.append(task)
        taken.add(task.id)
        added.append(task)
    return added


def next_runnable(subtasks: list[SubTask]) -> SubTask | None:
    by_id = {task.id: task for task in subtasks}
    for task in subtasks:
        if task.status != "pending" or task.owner == "reviewer":
            continue
        failed_dep = any(
            dependency in by_id and by_id[dependency].status == "failed"
            for dependency in task.depends_on
        )
        if failed_dep:
            task.status = "blocked"
            task.result = "Blocked because a dependency failed."
            continue
        ready = all(
            dependency in by_id and by_id[dependency].status == "done"
            for dependency in task.depends_on
        )
        if ready:
            return task

    others_terminal = all(
        task.owner == "reviewer" or task.status in TERMINAL for task in subtasks
    )
    if not others_terminal:
        return None
    for task in subtasks:
        if task.status == "pending" and task.owner == "reviewer":
            return task
    return None
