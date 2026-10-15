"""Keyword overlap retrieval over an agent's past lessons."""

from __future__ import annotations

import re


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def rank_lessons(lessons: list[dict], query: str, limit: int = 3) -> list[dict]:
    query_tokens = tokens(query)
    scored: list[tuple[int, str, dict]] = []
    for lesson in lessons:
        haystack = f"{lesson.get('task', '')} {lesson.get('lesson', '')}"
        overlap = len(query_tokens & tokens(haystack))
        scored.append((overlap, str(lesson.get("timestamp", "")), lesson))
    positive = [item for item in scored if item[0] > 0]
    chosen = positive or scored
    chosen.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in chosen[:limit]]
