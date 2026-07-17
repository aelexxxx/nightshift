"""Morning reports and alerts, delivered by email (falls back to disk)."""

from __future__ import annotations

import json
from datetime import datetime

from .config import Company, Settings


def _deliver(settings: Settings, company: Company, subject: str, body: str) -> None:
    to = company.owner_email or settings.owner_email
    delivered = False
    if to and settings.email_configured:
        try:
            from .tools.email_tools import smtp_send
            smtp_send(settings, to, subject, body)
            delivered = True
        except Exception as e:  # noqa: BLE001
            print(f"[warn] report email failed: {e}")
    reports = company.path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    (reports / f"{stamp}.md").write_text(f"# {subject}\n\n{body}\n", encoding="utf-8")
    if not delivered:
        print(f"[info] report saved to {reports} (email not configured/failed)")


def send_morning_report(settings: Settings, company: Company, ceo_summary: str,
                        run_meta: dict, reflection: dict) -> None:
    grade = reflection.get("grade", "—")
    body = f"""{ceo_summary.strip() or '(the CEO produced no final summary)'}

────────────────────────────────
Run metadata
- Cost this run:   ${run_meta.get('cost_usd', 0):.2f}
- Turns:           {run_meta.get('turns')}
- Duration:        {run_meta.get('duration_min')} min
- Self-grade:      {grade}/10
- Reflection:      {reflection.get('summary', '—')}

Ledger
{json.dumps(run_meta.get('ledger', {}), indent=2)}

Journal: companies/{company.slug}/journal/{run_meta.get('date')}.md
Pause anytime:  nightshift pause {company.slug}
"""
    subject = f"[{company.name}] Morning report — {run_meta.get('date')}"
    _deliver(settings, company, subject, body)


def send_alert(settings: Settings, company: Company, message: str) -> None:
    _deliver(settings, company, f"[{company.name}] nightshift alert", message)
