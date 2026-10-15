"""Completion-rate bookkeeping and lesson retrieval."""

from __future__ import annotations

import unittest

from src.chat.models import RunRecord
from src.memory.retrieve import rank_lessons
from src.metrics.report import render_report
from src.orchestrator.delegator import make_subtask, next_runnable


class MetricsTests(unittest.TestCase):
    def test_completion_rate_counts_finished_subtasks(self) -> None:
        record = RunRecord(
            task_id="sample",
            goal="goal",
            mode="group",
            started_at="t0",
            ended_at="t1",
            seconds=1.25,
            subtasks=[
                {"id": "a", "status": "done"},
                {"id": "b", "status": "done"},
                {"id": "c", "status": "failed"},
            ],
            fatal=False,
            conversation_id="c1",
        )
        self.assertAlmostEqual(record.completion_rate, 2 / 3)
        self.assertFalse(record.success)

    def test_report_includes_time_and_completion(self) -> None:
        record = RunRecord(
            task_id="sample",
            goal="goal",
            mode="group",
            started_at="t0",
            ended_at="t1",
            seconds=1.5,
            subtasks=[{"id": "a", "owner": "researcher", "status": "done", "result": "ok"}],
            fatal=False,
            conversation_id="c1",
            criteria_met=True,
        )
        report = render_report([record])
        self.assertIn("100%", report)
        self.assertIn("1.500", report)
        self.assertIn("Harness criteria met: 100%", report)

    def test_reviewer_waits_for_spawned_coder(self) -> None:
        research = make_subtask("researcher", "Gather notes", "goal", existing_ids=set())
        research.id = "research"
        research.status = "done"
        review = make_subtask("reviewer", "Review", "check", depends_on=["research"])
        coder = make_subtask("coder", "Implement", "goal", depends_on=["research"])
        coder.status = "pending"
        runnable = next_runnable([research, review, coder])
        self.assertIsNotNone(runnable)
        self.assertEqual(runnable.owner, "coder")

    def test_retrieval_prefers_overlapping_lessons(self) -> None:
        lessons = [
            {"task": "unrelated cooking notes", "lesson": "Boil water.", "timestamp": "1"},
            {
                "task": "Write Fibonacci numbers in Markdown",
                "lesson": "Completed the Fibonacci script.",
                "timestamp": "2",
            },
        ]
        ranked = rank_lessons(lessons, "Fibonacci Markdown report", limit=1)
        self.assertEqual(ranked[0]["lesson"], "Completed the Fibonacci script.")


if __name__ == "__main__":
    unittest.main()
