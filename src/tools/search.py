"""Web search. Offline mode returns a local note so the demo still runs."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from src.config import SEARCH_TIMEOUT_SEC
from src.tools.context import ToolContext


def search(ctx: ToolContext, query: str) -> str:
    if ctx.offline:
        return (
            f"Offline search note for '{query}'. "
            "No live results were requested. Use the task statement as the source."
        )
    encoded = urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    )
    request = urllib.request.Request(
        f"https://api.duckduckgo.com/?{encoded}",
        headers={"User-Agent": "multi-agent-platform-prototype"},
    )
    try:
        with urllib.request.urlopen(request, timeout=SEARCH_TIMEOUT_SEC) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return f"Search failed ({exc}). Continue from the task statement."

    lines = [f"Query: {query}"]
    abstract = (payload.get("AbstractText") or "").strip()
    if abstract:
        lines.append(abstract)
    for topic in payload.get("RelatedTopics") or []:
        if isinstance(topic, dict) and topic.get("Text"):
            lines.append(str(topic["Text"]))
        if len(lines) >= 7:
            break
    if len(lines) == 1:
        return f"No live results for '{query}'. Continue from the task statement."
    return "\n".join(lines)
