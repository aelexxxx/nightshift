"""Self-optimization: after every run, a reflection pass grades the night,
extracts lessons, and rewrites the company's prompt-override layer.

The override file is re-injected into the CEO system prompt on the next run,
so the system's operating instructions literally improve themselves — with
hard limits (size cap, no touching base prompts, versioned on disk)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from .config import PROMPTS_DIR, Company, Settings

MAX_OVERRIDE_CHARS = 6000
MAX_TAIL = 12000


def _tail(path: Path, limit: int = MAX_TAIL) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a response (with or without fences)."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fence.group(1)] if fence else []
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    for c in candidates:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return {}


async def reflect(settings: Settings, company: Company, journal_file: Path) -> dict:
    """Run the reflection pass. Returns {} on any failure — never blocks the run."""
    system = (PROMPTS_DIR / "self_optimization.md").read_text(encoding="utf-8")
    current_overrides = _tail(company.overrides_file, MAX_OVERRIDE_CHARS)
    kpis = _tail(company.path / "kpis.csv", 3000)
    lessons = _tail(company.memory / "LESSONS.md", 4000)

    prompt = f"""Company: {company.name}
Mission: {company.mission}

## Tonight's journal
{_tail(journal_file)}

## KPI history (tail)
{kpis or '(none yet)'}

## Existing lessons (tail)
{lessons or '(none yet)'}

## Current prompt overrides
{current_overrides or '(empty)'}

Grade tonight's run and produce the JSON object described in your instructions."""

    model = os.environ.get("NIGHTSHIFT_REFLECT_MODEL", "") or company.model or settings.model
    options = ClaudeAgentOptions(
        system_prompt=system,
        model=model,
        max_turns=2,
        allowed_tools=[],
        cwd=str(company.path),
        setting_sources=[],
    )

    try:
        text = ""
        async for message in query(prompt=prompt, options=options):
            if type(message).__name__ == "ResultMessage":
                text = getattr(message, "result", "") or ""
        data = _extract_json(text)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] reflection failed: {e}")
        return {}

    if not data:
        return {}

    # Apply lessons
    new_lessons = [str(l).strip() for l in data.get("lessons", []) if str(l).strip()]
    if new_lessons:
        company.memory.mkdir(parents=True, exist_ok=True)
        lessons_file = company.memory / "LESSONS.md"
        with lessons_file.open("a", encoding="utf-8") as f:
            for lesson in new_lessons:
                f.write(f"- ({journal_file.stem}) {lesson}\n")

    # Apply prompt overrides (size-capped, full replacement)
    overrides_md = str(data.get("overrides_md", "")).strip()
    if overrides_md:
        company.overrides_file.parent.mkdir(parents=True, exist_ok=True)
        company.overrides_file.write_text(overrides_md[:MAX_OVERRIDE_CHARS],
                                          encoding="utf-8")

    # Record grade
    grade = data.get("grade")
    if isinstance(grade, (int, float)):
        kpi_file = company.path / "kpis.csv"
        new = not kpi_file.exists()
        with kpi_file.open("a", encoding="utf-8") as f:
            if new:
                f.write("date,name,value,note\n")
            f.write(f"{journal_file.stem},self_grade,{grade},reflection\n")

    return data
