"""Skills: reusable craft knowledge in skills/<name>/SKILL.md.

Skills are linkable per company (company.yaml `skills: all` or a list).
Only a compact index goes into the system prompt; agents Read the full
SKILL.md on demand — progressive disclosure keeps the prompt lean while
every project shares the same evolving craft library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT

SKILLS_DIR = REPO_ROOT / "skills"


@dataclass
class Skill:
    name: str
    description: str
    path: Path


def _parse_frontmatter(md: str) -> dict:
    meta: dict = {}
    if md.startswith("---"):
        try:
            _, front, _ = md.split("---", 2)
            for line in front.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
        except ValueError:
            pass
    return meta


def load_skills(selection: str | list[str] = "all") -> list[Skill]:
    if not SKILLS_DIR.exists():
        return []
    wanted = None if selection == "all" else {s.strip() for s in selection}
    skills = []
    for f in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        name = f.parent.name
        if wanted is not None and name not in wanted:
            continue
        meta = _parse_frontmatter(f.read_text(encoding="utf-8"))
        skills.append(Skill(
            name=meta.get("name", name),
            description=meta.get("description", ""),
            path=f,
        ))
    return skills


def index_block(skills: list[Skill]) -> str:
    """Markdown block for the CEO system prompt."""
    if not skills:
        return ""
    lines = [
        "\n## Skills library",
        "",
        "Craft playbooks shared across all companies. BEFORE doing work of a "
        "kind listed here, Read the skill file first and follow it — skills "
        "encode hard-won standards and outrank your defaults. Cite in the "
        "journal which skills you used.",
        "",
    ]
    for s in skills:
        lines.append(f"- **{s.name}** — {s.description}\n  → Read: {s.path}")
    return "\n".join(lines) + "\n"
