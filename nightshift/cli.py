"""nightshift CLI.

  nightshift new <slug> --name "..." --mission "..."   scaffold a company
  nightshift run <slug> [--task "..."]                 run one night now
  nightshift daemon                                    schedule all companies nightly
  nightshift list                                      companies + status
  nightshift status <slug>                             ledger/budget detail
  nightshift pause <slug> | resume <slug>              kill switch
  nightshift doctor                                    check config & prerequisites
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from .config import (COMPANIES_DIR, TEMPLATE_DIR, list_companies, load_company,
                     load_settings)
from .ledger import Ledger


def cmd_new(args) -> int:
    slug = args.slug.strip().lower().replace(" ", "-")
    dest = COMPANIES_DIR / slug
    if dest.exists():
        print(f"companies/{slug} already exists.")
        return 1
    shutil.copytree(TEMPLATE_DIR, dest)
    yaml_file = dest / "company.yaml"
    text = yaml_file.read_text(encoding="utf-8")
    text = text.replace("name: My Company", f"name: {args.name or slug}")
    if args.mission:
        text = text.replace("mission: >\n  Describe the business",
                            f"mission: >\n  {args.mission}")
    yaml_file.write_text(text, encoding="utf-8")
    print(f"Created companies/{slug}/")
    print("Next steps:")
    print(f"  1. Edit companies/{slug}/company.yaml  (channels, caps, budget)")
    print(f"  2. Fill  companies/{slug}/IDEA.md      (the business brief — be specific)")
    print(f"  3. Fill  companies/{slug}/memory/VOICE.md (brand voice — avoids generic output)")
    print(f"  4. Test: nightshift run {slug}")
    return 0


def cmd_run(args) -> int:
    from .engine import run_night
    settings = load_settings()
    if not settings.has_model_auth:
        print("No model auth found. Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN in .env")
        return 1
    path = COMPANIES_DIR / args.slug
    if not (path / "company.yaml").exists():
        print(f"Unknown company: {args.slug}")
        return 1
    meta = asyncio.run(run_night(path, settings, extra_task=args.task or ""))
    print(json.dumps(meta, indent=2))
    return 0


def cmd_daemon(_args) -> int:
    from .scheduler import daemon
    settings = load_settings()
    if not settings.has_model_auth:
        print("No model auth found. Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN in .env")
        return 1
    try:
        asyncio.run(daemon(settings))
    except KeyboardInterrupt:
        print("\ndaemon stopped.")
    return 0


def cmd_list(_args) -> int:
    companies = list_companies()
    if not companies:
        print("No companies yet. Create one: nightshift new <slug> --name '...'")
        return 0
    for path in companies:
        c = load_company(path)
        ledger = Ledger(c)
        state = "PAUSED" if c.paused else "active"
        print(f"{c.slug:24} {state:7} "
              f"${ledger.month_spend():6.2f}/${c.monthly_budget_usd:<6.2f} "
              f"autonomy={c.autonomy}")
    return 0


def cmd_status(args) -> int:
    path = COMPANIES_DIR / args.slug
    c = load_company(path)
    print(json.dumps(Ledger(c).status(), indent=2))
    latest = sorted(c.journal.glob("*.md"))
    if latest:
        print(f"\nLatest journal: {latest[-1]}")
    return 0


def cmd_pause(args) -> int:
    (COMPANIES_DIR / args.slug / "PAUSED").touch()
    print(f"{args.slug} paused. Resume with: nightshift resume {args.slug}")
    return 0


def cmd_resume(args) -> int:
    f = COMPANIES_DIR / args.slug / "PAUSED"
    f.unlink(missing_ok=True)
    print(f"{args.slug} resumed.")
    return 0


def cmd_doctor(_args) -> int:
    settings = load_settings()
    checks = [
        ("Model auth (API key or OAuth token)", settings.has_model_auth),
        ("Node.js ≥ 18 (required by the Agent SDK runtime)",
         shutil.which("node") is not None),
        ("Owner email set", bool(settings.owner_email)),
        ("Email channel (SMTP)", settings.email_configured),
        ("Email inbox (IMAP)", settings.imap_configured),
        ("X / Twitter credentials", settings.x_configured),
        ("GitHub token", settings.github_configured),
        ("Company template present", TEMPLATE_DIR.exists()),
    ]
    ok = True
    for label, passed in checks:
        print(f"  {'✓' if passed else '✗'}  {label}")
        if label.startswith(("Model auth", "Node.js", "Company template")) and not passed:
            ok = False
    print("\nRequired checks passed." if ok
          else "\nFix the ✗ items marked required (model auth, Node.js, template).")
    print("Channels that are not configured are simply disabled for agents.")
    return 0 if ok else 1


def main() -> None:
    p = argparse.ArgumentParser(prog="nightshift",
                                description="Self-hosted autonomous company operator.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("new", help="scaffold a new company")
    s.add_argument("slug")
    s.add_argument("--name", default="")
    s.add_argument("--mission", default="")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("run", help="run one night now for a company")
    s.add_argument("slug")
    s.add_argument("--task", default="", help="extra directive for tonight")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("daemon", help="run all companies nightly")
    s.set_defaults(func=cmd_daemon)

    s = sub.add_parser("list", help="list companies")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("status", help="ledger status for a company")
    s.add_argument("slug")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("pause", help="pause a company (kill switch)")
    s.add_argument("slug")
    s.set_defaults(func=cmd_pause)

    s = sub.add_parser("resume", help="resume a paused company")
    s.add_argument("slug")
    s.set_defaults(func=cmd_resume)

    s = sub.add_parser("doctor", help="check configuration")
    s.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
