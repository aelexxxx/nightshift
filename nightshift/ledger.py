"""Ledger: per-company spend tracking, daily channel caps, suppression list.

This is the hard guardrail layer. Tools call it before any outbound action;
prompts alone are never trusted to enforce limits.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .config import Company


class Ledger:
    def __init__(self, company: Company):
        self.company = company
        self.file = company.path / "ledger.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"months": {}, "days": {}}

    def _save(self) -> None:
        self.file.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # ── Spend ────────────────────────────────────────────────────────────
    @staticmethod
    def _month_key(d: date | None = None) -> str:
        d = d or date.today()
        return d.strftime("%Y-%m")

    @staticmethod
    def _day_key(d: date | None = None) -> str:
        d = d or date.today()
        return d.isoformat()

    def month_spend(self) -> float:
        return float(self.data["months"].get(self._month_key(), {}).get("cost_usd", 0.0))

    def budget_remaining(self) -> float:
        return self.company.monthly_budget_usd - self.month_spend()

    def budget_ok(self) -> bool:
        return self.budget_remaining() > 0

    def record_cost(self, usd: float) -> None:
        m = self.data["months"].setdefault(self._month_key(), {"cost_usd": 0.0, "runs": 0})
        m["cost_usd"] = round(float(m["cost_usd"]) + float(usd), 6)
        m["runs"] = int(m.get("runs", 0)) + 1
        self._save()

    # ── Channel caps ─────────────────────────────────────────────────────
    def _day(self) -> dict:
        return self.data["days"].setdefault(self._day_key(), {})

    def used_today(self, channel: str) -> int:
        return int(self._day().get(channel, 0))

    def cap_for(self, channel: str) -> int:
        if channel == "email":
            return self.company.email.daily_cap
        if channel == "twitter":
            return self.company.twitter.daily_cap
        return 10_000

    def can_use(self, channel: str) -> tuple[bool, str]:
        cap = self.cap_for(channel)
        used = self.used_today(channel)
        if used >= cap:
            return False, (f"Daily {channel} cap reached ({used}/{cap}). "
                           f"Resets at midnight local time.")
        return True, f"{used}/{cap} used today"

    def record_use(self, channel: str, n: int = 1) -> None:
        day = self._day()
        day[channel] = int(day.get(channel, 0)) + n
        self._save()

    # ── Suppression list (opt-outs — never emailed again) ────────────────
    @property
    def suppression_file(self) -> Path:
        return self.company.memory / "suppression.txt"

    def suppressed(self, address: str) -> bool:
        if not self.suppression_file.exists():
            return False
        entries = {
            line.split("#", 1)[0].strip().lower()
            for line in self.suppression_file.read_text(encoding="utf-8").splitlines()
        }
        return address.strip().lower() in entries

    def suppress(self, address: str, reason: str = "") -> None:
        self.suppression_file.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        with self.suppression_file.open("a", encoding="utf-8") as f:
            f.write(f"{address.strip().lower()}  # {stamp} {reason}\n".rstrip() + "\n")

    # ── Status summary ───────────────────────────────────────────────────
    def status(self) -> dict:
        return {
            "month": self._month_key(),
            "spend_usd": round(self.month_spend(), 4),
            "budget_usd": self.company.monthly_budget_usd,
            "remaining_usd": round(self.budget_remaining(), 4),
            "today": {
                "email": f"{self.used_today('email')}/{self.cap_for('email')}",
                "twitter": f"{self.used_today('twitter')}/{self.cap_for('twitter')}",
            },
        }
