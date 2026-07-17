"""Goal loop: you hand the system measurable targets (goals.yaml); every run
sees its live progress, the weekly review re-plans against the lagging goal,
and the reflection pass grades nights by goal progress — so the loop keeps
pointing at what you asked for, not at what's fun to do."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

import yaml

from .config import Company

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday"]


def load_goals(company: Company) -> dict:
    f = company.path / "goals.yaml"
    if not f.exists():
        return {}
    try:
        return yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"[warn] invalid goals.yaml: {e}")
        return {}


def latest_kpis(company: Company) -> dict[str, tuple[float, str]]:
    """Latest logged value per KPI name: {name: (value, date)}."""
    f = company.path / "kpis.csv"
    out: dict[str, tuple[float, str]] = {}
    if not f.exists():
        return out
    try:
        with f.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                try:
                    value = float(row.get("value") or 0)
                except ValueError:
                    continue
                out[name] = (value, (row.get("date") or "").strip())
    except (OSError, csv.Error) as e:
        print(f"[warn] could not read kpis.csv: {e}")
    return out


def _progress_line(goal: dict, kpis: dict[str, tuple[float, str]]) -> str:
    metric = str(goal.get("metric", "")).strip()
    target = goal.get("target")
    by = str(goal.get("by", "")).strip()
    if not metric or target is None:
        return ""
    deadline = ""
    if by:
        try:
            days = (datetime.strptime(by, "%Y-%m-%d").date() - date.today()).days
            deadline = f" by {by} ({days}d left)" if days >= 0 else f" by {by} (OVERDUE {-days}d)"
        except ValueError:
            deadline = f" by {by}"
    if metric in kpis:
        value, logged = kpis[metric]
        try:
            pct = f", {value / float(target) * 100:.0f}%" if float(target) else ""
        except (ValueError, ZeroDivisionError):
            pct = ""
        return f"- {metric}: {value:g} / {target}{deadline}{pct} (last logged {logged})"
    return f"- {metric}: NO DATA YET / {target}{deadline} — instrument this first"


def goals_block(company: Company) -> str:
    """Markdown block for the system prompt and the reflection pass."""
    goals = load_goals(company)
    if not goals:
        return ""
    kpis = latest_kpis(company)
    lines = ["\n## Goals — the loop you are optimizing\n"]
    if goals.get("north_star"):
        lines.append(f"North star: {goals['north_star']}\n")
    for g in goals.get("goals", []) or []:
        line = _progress_line(g, kpis)
        if line:
            lines.append(line)
    lines.append(
        "\nEvery night must move at least one lagging goal or fix why it "
        "can't be measured. Progress on goals outranks all other work."
    )
    return "\n".join(lines) + "\n"


def is_review_day(company: Company, today: date | None = None) -> bool:
    goals = load_goals(company)
    day = str(goals.get("review_day", "")).strip().lower()
    if day not in WEEKDAYS:
        return False
    return (today or date.today()).weekday() == WEEKDAYS.index(day)
