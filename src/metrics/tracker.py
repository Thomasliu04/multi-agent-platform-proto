"""Collect completion, crashes, and elapsed time for each run."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from src.chat.models import RunRecord, utc_now


class Metrics:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.runs: list[RunRecord] = []

    def begin(self) -> float:
        return perf_counter()

    def finish(
        self,
        task_id: str,
        goal: str,
        mode: str,
        started: float,
        subtasks: list[dict],
        fatal: bool,
        conversation_id: str,
        transcript: list[str],
        started_at: str | None = None,
    ) -> RunRecord:
        record = RunRecord(
            task_id=task_id,
            goal=goal,
            mode=mode,
            started_at=started_at or utc_now(),
            ended_at=utc_now(),
            seconds=round(perf_counter() - started, 3),
            subtasks=subtasks,
            fatal=fatal,
            conversation_id=conversation_id,
            transcript=transcript,
        )
        self.runs.append(record)
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "runs.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "task_id": record.task_id,
                        "goal": record.goal,
                        "mode": record.mode,
                        "seconds": record.seconds,
                        "completion_rate": record.completion_rate,
                        "success": record.success,
                        "fatal": record.fatal,
                        "subtasks": record.subtasks,
                    }
                )
                + "\n"
            )
        return record
