"""Tools that let the agent see its own budget/limits and record KPIs."""

from __future__ import annotations

import csv
import json
from datetime import date

from claude_agent_sdk import tool

from ..config import Company
from ..ledger import Ledger


def build_ledger_tools(company: Company, ledger: Ledger) -> list:
    from . import err, ok

    @tool(
        "get_budget_status",
        "Check remaining monthly model budget and today's channel usage "
        "(email sends, tweets). Call this before planning outreach volume.",
        {},
    )
    async def get_budget_status(args: dict) -> dict:  # noqa: ARG001
        return ok(json.dumps(ledger.status(), indent=2))

    @tool(
        "log_kpi",
        "Record a KPI measurement for this company (appended to kpis.csv). "
        "Log every KPI you can observe each run — trends drive next-night "
        "priorities and self-optimization.",
        {"name": str, "value": float, "note": str},
    )
    async def log_kpi(args: dict) -> dict:
        name = str(args.get("name", "")).strip()
        if not name:
            return err("name is required.")
        try:
            value = float(args.get("value", 0))
        except (TypeError, ValueError):
            return err("value must be a number.")
        f = company.path / "kpis.csv"
        new = not f.exists()
        with f.open("a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["date", "name", "value", "note"])
            w.writerow([date.today().isoformat(), name, value,
                        str(args.get("note", ""))])
        return ok(f"KPI logged: {name}={value}")

    return [get_budget_status, log_kpi]
