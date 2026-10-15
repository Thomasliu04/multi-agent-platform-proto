"""Sandboxed read, write, update, and delete for plain-text files."""

from __future__ import annotations

from src.tools.context import ToolContext


def _target(ctx: ToolContext, path: str):
    target = ctx.workspace.resolve_agent_path(ctx.agent_id, path)
    ctx.workspace.check_suffix(target, ctx.agent_id)
    return target


def write_file(ctx: ToolContext, path: str, content: str) -> str:
    target = _target(ctx, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {path} ({len(content)} characters)."


def read_file(ctx: ToolContext, path: str) -> str:
    target = ctx.workspace.resolve_agent_path(ctx.agent_id, path)
    if not target.is_file():
        return f"File not found: {path}"
    text = target.read_text(encoding="utf-8")
    if len(text) > 20000:
        return text[:20000] + "\n...[truncated]"
    return text


def update_file(ctx: ToolContext, path: str, old: str, new: str) -> str:
    target = _target(ctx, path)
    if not target.is_file():
        return f"File not found: {path}"
    text = target.read_text(encoding="utf-8")
    if old not in text:
        return "The text to replace was not found."
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"Updated {path}."


def delete_file(ctx: ToolContext, path: str) -> str:
    target = ctx.workspace.resolve_agent_path(ctx.agent_id, path)
    if not target.is_file():
        return f"File not found: {path}"
    target.unlink()
    return f"Deleted {path}."


def list_files(ctx: ToolContext) -> str:
    root = ctx.workspace.agent_root(ctx.agent_id)
    names = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            names.append(path.relative_to(root).as_posix())
    return "\n".join(names) if names else "(empty)"


def publish_handoff(ctx: ToolContext, path: str) -> str:
    source = _target(ctx, path)
    if source.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("Only .md and .txt files can be published to the handoff folder.")
    if not source.is_file():
        return f"File not found: {path}"
    destination = ctx.workspace.handoff / source.name
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return f"Published {source.name} to the handoff folder."


def list_handoff(ctx: ToolContext) -> str:
    names = sorted(path.name for path in ctx.workspace.handoff.iterdir() if path.is_file())
    return "\n".join(names) if names else "(empty)"


def read_handoff(ctx: ToolContext, name: str) -> str:
    if any(part in name for part in ("/", "\\", "..")):
        raise PermissionError(f"Handoff name must be a single file name, got '{name}'.")
    path = (ctx.workspace.handoff / name).resolve()
    handoff = ctx.workspace.handoff.resolve()
    if handoff not in path.parents:
        raise PermissionError(f"Path escapes the handoff folder: {name}")
    if not path.is_file():
        return f"Handoff file not found: {name}"
    text = path.read_text(encoding="utf-8")
    if len(text) > 20000:
        return text[:20000] + "\n...[truncated]"
    return text
