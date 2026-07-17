"""Loads subagent definitions from prompts/agents/*.md.

File format: optional '---' frontmatter with a 'description:' line, then the
agent's system prompt. The filename (minus .md) becomes the agent name.
"""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import AgentDefinition

from .config import PROMPTS_DIR


def _parse(md: str) -> tuple[str, str]:
    """Return (description, prompt)."""
    description = ""
    body = md
    if md.startswith("---"):
        try:
            _, front, body = md.split("---", 2)
            for line in front.splitlines():
                if line.strip().startswith("description:"):
                    description = line.split(":", 1)[1].strip()
        except ValueError:
            body = md
    return description or "Specialist agent.", body.strip()


def load_subagents() -> dict[str, AgentDefinition]:
    agents_dir = PROMPTS_DIR / "agents"
    agents: dict[str, AgentDefinition] = {}
    if not agents_dir.exists():
        return agents
    for f in sorted(agents_dir.glob("*.md")):
        description, prompt = _parse(f.read_text(encoding="utf-8"))
        agents[f.stem] = AgentDefinition(description=description, prompt=prompt)
    return agents
