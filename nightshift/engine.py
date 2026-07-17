"""The nightly run: assemble context → run the CEO session → reflect → report."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from . import goals as goals_mod
from . import reporting, selfopt
from .agents import load_subagents
from .config import PROMPTS_DIR, REPO_ROOT, Company, Settings, load_company
from .ledger import Ledger
from .skills import index_block, load_skills
from .tools import build_company_mcp_server


def _load_external_mcp_servers(company: Company) -> dict:
    """Merge repo-level mcp.json with company-level mcp.json (company wins)."""
    servers: dict = {}
    for f in (REPO_ROOT / "mcp.json", company.path / "mcp.json"):
        if f.exists():
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                servers.update(raw.get("mcpServers", {}))
            except json.JSONDecodeError as e:
                print(f"[warn] Skipping invalid {f}: {e}")
    servers.pop("_comment", None)
    return servers


def _system_prompt(settings: Settings, company: Company, ledger: Ledger) -> str:
    base = (PROMPTS_DIR / "ceo.md").read_text(encoding="utf-8")
    standards_file = PROMPTS_DIR / "standards.md"
    if standards_file.exists():
        base += "\n\n" + standards_file.read_text(encoding="utf-8")

    channels = []
    if company.email.enabled and settings.email_configured:
        channels.append(f"email (cap {company.email.daily_cap}/day)")
    if company.twitter.enabled and settings.x_configured:
        channels.append(f"twitter (cap {company.twitter.daily_cap}/day)")
    if company.github and settings.github_configured:
        channels.append("github")

    profile = f"""
## Company profile (from company.yaml — read-only facts)

- Name: {company.name}
- Mission: {company.mission or '(see IDEA.md)'}
- Autonomy: {company.autonomy} ({'you act directly' if company.autonomy == 'full' else 'outbound messages are queued for human approval'})
- Cold outreach allowed: {'yes' if company.cold_outreach else 'NO — only contact people with an existing relationship, inbound interest, or explicit opt-in'}
- Enabled channels: {', '.join(channels) or 'none (work internally, queue drafts)'}
- KPIs to track: {', '.join(company.kpis) or 'define sensible KPIs yourself and log them'}
- Owner email (your human): {company.owner_email or settings.owner_email}

## Guardrail status right now

{json.dumps(ledger.status(), indent=2)}
"""

    overrides = ""
    if company.overrides_file.exists():
        text = company.overrides_file.read_text(encoding="utf-8").strip()
        if text:
            overrides = ("\n## Learned overrides (self-optimized — follow these, "
                         "they encode past lessons)\n\n" + text + "\n")

    skills = index_block(load_skills(company.skills))
    goals = goals_mod.goals_block(company)

    return base + profile + goals + skills + overrides


NIGHTLY_PROMPT = """Tonight's run for {name} — {today}.

Follow the Nightly Protocol from your system prompt. In short:
1. Orient: read IDEA.md, STATE.md, memory/ (VOICE.md, AUDIENCE.md, LESSONS.md), \
the last 2 journal entries, and check_inbox + get_budget_status. If a github repo \
exists, check open issues.
2. Decide the single highest-leverage objective for tonight, plus at most 2 \
secondary tasks. Write the plan down first.
3. Execute with your subagents and tools. Ship real things.
4. Record: log KPIs, update STATE.md, append memory files as needed, and write \
tonight's journal to journal/{today}.md (create it; format per protocol).
5. Your FINAL message must be the Morning Report (per protocol) — it will be \
emailed to the owner verbatim.
{extra}"""


async def run_night(company_path: Path, settings: Settings,
                    extra_task: str = "", verbose: bool = True) -> dict:
    """Execute one full nightly run for a company. Returns a result summary."""
    company = load_company(company_path)
    ledger = Ledger(company)
    today = date.today().isoformat()

    if company.paused:
        return {"skipped": f"{company.slug} is paused (PAUSED file present)."}
    if not ledger.budget_ok():
        reporting.send_alert(settings, company,
                             f"Monthly budget exhausted "
                             f"(${ledger.month_spend():.2f}/"
                             f"${company.monthly_budget_usd:.2f}). Run skipped.")
        return {"skipped": f"{company.slug}: monthly budget exhausted."}

    # Ensure expected directories exist
    for d in (company.workspace, company.memory, company.journal, company.outbox,
              company.overrides_file.parent):
        d.mkdir(parents=True, exist_ok=True)

    mcp_servers: dict = {"company": build_company_mcp_server(settings, company, ledger)}
    mcp_servers.update(_load_external_mcp_servers(company))

    env = {}
    for key in ("GITHUB_TOKEN", "GITHUB_USER"):
        if os.environ.get(key):
            env[key] = os.environ[key]

    options = ClaudeAgentOptions(
        system_prompt=_system_prompt(settings, company, ledger),
        model=company.model or settings.model,
        cwd=str(company.path),
        permission_mode="bypassPermissions",
        max_turns=company.max_turns,
        mcp_servers=mcp_servers,
        agents=load_subagents(),
        env=env,
        setting_sources=[],
    )

    extra = (f"\nAdditional directive from the owner (do this first): {extra_task}"
             if extra_task else "")
    weekly_file = PROMPTS_DIR / "weekly_review.md"
    if goals_mod.is_review_day(company) and weekly_file.exists():
        prompt = weekly_file.read_text(encoding="utf-8").format(
            name=company.name, today=today, extra=extra)
    else:
        prompt = NIGHTLY_PROMPT.format(name=company.name, today=today, extra=extra)

    started = datetime.now()
    final_text = ""
    cost_usd = 0.0
    num_turns = 0
    transcript: list[str] = []

    async for message in query(prompt=prompt, options=options):
        kind = type(message).__name__
        if kind == "AssistantMessage":
            for block in getattr(message, "content", []) or []:
                text = getattr(block, "text", None)
                if text:
                    transcript.append(text)
                    if verbose:
                        print(text)
                name = getattr(block, "name", None)
                if name and not text:
                    transcript.append(f"[tool: {name}]")
                    if verbose:
                        print(f"  → {name}")
        elif kind == "ResultMessage":
            final_text = getattr(message, "result", "") or ""
            cost_usd = float(getattr(message, "total_cost_usd", 0) or 0)
            num_turns = int(getattr(message, "num_turns", 0) or 0)

    ledger.record_cost(cost_usd)

    # Raw transcript for debugging
    raw_dir = company.journal / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / f"{today}.log").write_text("\n\n".join(transcript), encoding="utf-8")

    # Guarantee a journal entry exists even if the agent failed to write one
    journal_file = company.journal / f"{today}.md"
    if not journal_file.exists():
        journal_file.write_text(
            f"# {today} (engine fallback)\n\nThe agent did not write a journal "
            f"entry. Final message:\n\n{final_text}\n", encoding="utf-8")

    # Self-optimization pass (separate cheap call, no tools)
    reflection = await selfopt.reflect(settings, company, journal_file)

    duration_min = (datetime.now() - started).total_seconds() / 60
    run_meta = {
        "company": company.slug,
        "date": today,
        "cost_usd": round(cost_usd, 4),
        "turns": num_turns,
        "duration_min": round(duration_min, 1),
        "grade": reflection.get("grade"),
        "ledger": ledger.status(),
    }

    reporting.send_morning_report(settings, company, final_text, run_meta, reflection)
    return run_meta
