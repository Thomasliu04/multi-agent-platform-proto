"""Human-in-the-loop prompts. Callers block until an answer arrives."""

from __future__ import annotations


def approved(answer: str) -> bool:
    return answer.strip().lower() in {"y", "yes", "approve", "approved", "ok", "true"}


class HumanInterface:
    def ask(self, agent_id: str, question: str, kind: str) -> str:
        raise NotImplementedError


class CLIHuman(HumanInterface):
    def ask(self, agent_id: str, question: str, kind: str) -> str:
        prompt = "Approve? [y/N] " if kind == "permission" else "Answer: "
        try:
            text = input(prompt)
        except EOFError:
            text = ""
        if text.strip():
            return text.strip()
        if kind == "permission":
            return "no"
        return "Proceed with your best judgment."


class ScriptedHuman(HumanInterface):
    """Replay canned answers. Used by the demo, the eval runner, and tests."""

    def __init__(
        self,
        responses: list[str] | None = None,
        permission_default: str = "no",
        clarify_default: str = "Proceed with your best judgment.",
    ) -> None:
        self.responses = list(responses or [])
        self.permission_default = permission_default
        self.clarify_default = clarify_default
        self.log: list[dict] = []

    def ask(self, agent_id: str, question: str, kind: str) -> str:
        if self.responses:
            answer = self.responses.pop(0)
        elif kind == "permission":
            answer = self.permission_default
        else:
            answer = self.clarify_default
        self.log.append(
            {
                "agent": agent_id,
                "kind": kind,
                "question": question,
                "answer": answer,
            }
        )
        return answer
