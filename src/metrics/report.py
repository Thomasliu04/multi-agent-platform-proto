"""Markdown performance report."""

from __future__ import annotations

from src.chat.models import RunRecord


def render_report(records: list[RunRecord]) -> str:
    if not records:
        return "# Performance report\n\nNo runs recorded.\n"

    lines = [
        "# Performance report",
        "",
        "| Task | Mode | Subtask completion | Seconds | Fatal crash | Goal success | Criteria met |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for record in records:
        criteria = "n/a" if record.criteria_met is None else ("yes" if record.criteria_met else "no")
        lines.append(
            "| {task} | {mode} | {rate:.0%} | {seconds:.3f} | {fatal} | {success} | {criteria} |".format(
                task=record.task_id,
                mode=record.mode,
                rate=record.completion_rate,
                seconds=record.seconds,
                fatal="yes" if record.fatal else "no",
                success="yes" if record.success else "no",
                criteria=criteria,
            )
        )

    completion = sum(record.completion_rate for record in records) / len(records)
    elapsed = sum(record.seconds for record in records)
    goals = sum(1 for record in records if record.success)
    checked = [record for record in records if record.criteria_met is not None]
    criteria_rate = (
        sum(1 for record in checked if record.criteria_met) / len(checked) if checked else 0
    )
    lines.extend(
        [
            "",
            f"Mean subtask completion: {completion:.0%}",
            f"Goals completed without a failed subtask: {goals}/{len(records)}",
            f"Total execution time: {elapsed:.3f}s",
            f"Harness criteria met: {criteria_rate:.0%}" if checked else "Harness criteria met: n/a",
            "",
            "## Failure notes",
            "",
        ]
    )
    failures = []
    for record in records:
        for subtask in record.subtasks:
            if subtask["status"] != "done":
                failures.append(
                    f"- {record.task_id} / {subtask['id']} ({subtask['owner']}): {subtask['status']}"
                )
        if record.criteria_met is False:
            detail = "; ".join(record.criteria_notes) or "criteria were not met"
            failures.append(f"- {record.task_id} criteria: {detail}")
    lines.append("\n".join(failures) if failures else "No failed subtasks in this run.")
    lines.append("")
    return "\n".join(lines)
