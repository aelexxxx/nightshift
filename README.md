# nightshift

A self-hosted autonomous company operator, inspired by [Polsia](https://polsia.com):
every night an AI CEO wakes up, reads the state of your business, decides what
matters most, delegates to specialist agents (engineering, marketing, growth,
research), does real work through real channels — email, X/Twitter, GitHub,
any MCP server — learns from its own performance, and emails you a morning
report.

Unlike the hosted platforms there is no subscription and no per-seat fee.
Your only running cost is model usage (API tokens, or nothing extra on a
Claude Pro/Max subscription). Everything lives in plain files on your machine:
prompts, memory, journals, ledgers — all inspectable, all yours.

```
                        ┌──────────────────────────────┐
  02:00 nightly         │  CEO agent (Claude Agent SDK) │
  scheduler ──────────▶ │  orient → plan → execute →    │──▶ morning report
                        │  record → report              │      (email)
                        └──────┬───────────┬───────────┘
               Task tool       │           │  company MCP tools
        ┌──────────┬───────────┼─────┐     │  + your mcp.json servers
        ▼          ▼           ▼     ▼     ▼
   engineering  marketing   growth  research   email · X · GitHub · Stripe · …
        │          │           │     │
        └──────────┴───── writes to ┴──────────────┐
                                                   ▼
                    companies/<slug>/  (STATE.md, memory/, journal/, kpis.csv)
                                                   │
                     reflection pass (self-optimization) ──▶ prompt_overrides/
```

## How it stays sane (the guardrail layer)

Autonomy is enforced in *code*, not by trusting prompts:

- **Monthly model budget** per company; runs are skipped when it's exhausted.
- **Daily caps** for emails and tweets, checked inside the tools.
- **Suppression list**: one opt-out and an address can never be emailed again.
- **Autonomy modes**: `full` (sends directly) or `draft` (everything outbound
  waits in `outbox/pending/` for your approval).
- **Kill switch**: `nightshift pause <slug>` (or drop a `PAUSED` file).
- **Audit trail**: every send/post is logged to `outbox/`, every run to
  `journal/`, every dollar to `ledger.json`.

## Quickstart

Prerequisites: Python ≥ 3.10, Node.js ≥ 18 (the Agent SDK runtime uses it).

```bash
git clone <this repo> && cd nightshift
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env        # fill in what you have (see below)
nightshift doctor           # verify

nightshift new acme --name "Acme Tools" --mission "CLI tools for indie devs"
# → edit companies/acme/IDEA.md        (the business brief — be specific!)
# → edit companies/acme/memory/VOICE.md (brand voice — this kills generic output)
# → check companies/acme/company.yaml   (caps, budget, autonomy)

nightshift run acme         # one supervised night, watch it work
nightshift daemon           # then let it run every night
```

Tip for the first nights: set `autonomy: draft` in company.yaml and review
`outbox/pending/` each morning. Switch to `full` once you trust its taste.

### Model auth (pick one)

- **API key** (pay per token): set `ANTHROPIC_API_KEY`.
- **Claude Pro/Max subscription** (no extra cost): run `claude setup-token`
  once (requires the Claude Code CLI), put the result in
  `CLAUDE_CODE_OAUTH_TOKEN`.

### Channel credentials (all optional — unconfigured channels are disabled)

- **Email**: a Gmail address + [App Password](https://myaccount.google.com/apppasswords)
  (2FA required). Consider a dedicated address per company.
- **X/Twitter**: create an app at developer.x.com (free tier), generate OAuth
  1.0a user-context keys with Read & Write permission.
- **GitHub**: a personal access token with repo scope.

## Daily operation

| Command | Effect |
|---|---|
| `nightshift daemon` | run all companies nightly at `NIGHTSHIFT_RUN_AT`, staggered 20 min |
| `nightshift run <slug>` | one night right now |
| `nightshift run <slug> --task "..."` | one night with a priority directive from you |
| `nightshift list` / `status <slug>` | spend, caps, state |
| `nightshift pause <slug>` / `resume <slug>` | kill switch |

Prefer cron/systemd on a server? See `scripts/cron.example`. Multiple
companies just work — each is an isolated folder with its own budget, memory,
and overrides. Add more with `nightshift new`.

## The self-optimization loop

After every run a cheap reflection pass reads the journal and KPI history,
grades the night (logged as `self_grade` in kpis.csv), extracts durable
lessons into `memory/LESSONS.md`, and rewrites
`prompt_overrides/OVERRIDES.md` — a size-capped playbook injected into the
CEO's system prompt on the next run. The system literally edits its own
operating instructions, within limits: it can change tactics and priorities
but can never weaken the consent/safety rules, and everything it writes is a
plain file you can read, edit, or delete. Commit the repo to git and you get
full version history of the system's "personality" over time.

## Swapping models

- Per company: `model:` in company.yaml. Globally: `NIGHTSHIFT_MODEL` in .env.
  Any Claude model id works (Haiku for cheap nights, Sonnet default, Opus for
  hard problems).
- Reflection pass model: `NIGHTSHIFT_REFLECT_MODEL` (set it to a Haiku-class
  model to save money).
- Non-Claude models: the Agent SDK speaks the Anthropic Messages API, so point
  `ANTHROPIC_BASE_URL` at any Anthropic-compatible gateway (e.g. a
  [LiteLLM proxy](https://docs.litellm.ai) fronting other providers), or use
  the SDK's native Bedrock/Vertex support (`CLAUDE_CODE_USE_BEDROCK=1` /
  `CLAUDE_CODE_USE_VERTEX=1`). Tool-use quality varies a lot between models;
  test on `draft` autonomy first.

## Extending with MCP (any tool you want)

Copy `mcp.json.example` → `mcp.json` (repo-wide) or put an `mcp.json` inside a
company folder (company-specific). Any stdio or HTTP MCP server appears as
tools to the CEO automatically — Stripe, Notion, Slack, analytics, databases,
whatever exists in the MCP ecosystem. Details in `docs/EXTENDING.md`.

## Costs

- Model: a focused ~100-turn Sonnet night typically lands in the low single
  dollars; Haiku nights cost cents. `monthly_budget_usd` caps it per company.
  On a Claude subscription: no marginal cost until you hit plan limits.
- X API free tier, Gmail, GitHub: $0.
- Anything the agent *builds* that needs paid services (domains, hosting) goes
  through the "Needs from you" list — it can't spend your money.

## Read before going full-auto

`docs/SAFETY.md` — legal notes on outreach (GDPR/UWG/CAN-SPAM), X automation
rules, and why `cold_outreach` defaults to `false`. Short version: the system
is built to behave like a careful human operator, and the defaults keep you
inside the lines; loosen them deliberately, not accidentally.

## Layout

```
nightshift/            engine, scheduler, CLI, tools (the code)
prompts/               CEO + subagent prompts, reflection rubric (the soul)
companies/_template/   copied by `nightshift new`
companies/<slug>/      one folder per business: config, state, memory,
                       journal, outbox, ledger, kpis, overrides
docs/                  SAFETY.md, EXTENDING.md
scripts/cron.example   cron/systemd alternative to the daemon
```
