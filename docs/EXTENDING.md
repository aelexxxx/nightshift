# Extending nightshift

## Adding tools via MCP

Any MCP server becomes agent tooling with zero code changes.

1. Repo-wide: copy `mcp.json.example` → `mcp.json`.
2. Per company: create `companies/<slug>/mcp.json` (same format; entries with
   the same name override repo-wide ones).

```json
{
  "mcpServers": {
    "stripe":   { "type": "stdio", "command": "npx",
                  "args": ["-y", "@stripe/mcp", "--tools=all"],
                  "env": { "STRIPE_SECRET_KEY": "sk_..." } },
    "postgres": { "type": "stdio", "command": "npx",
                  "args": ["-y", "@modelcontextprotocol/server-postgres",
                           "postgresql://localhost/acme"] },
    "internal": { "type": "http", "url": "https://tools.example.com/mcp",
                  "headers": { "Authorization": "Bearer ..." } }
  }
}
```

The CEO discovers these tools automatically. Mention new capabilities in the
company's IDEA.md ("you have Stripe access — check MRR nightly") so they get
used deliberately, and add a KPI so usage is measured.

Good candidates from the ecosystem: Stripe (revenue), Slack (notifications to
you), Notion (shared docs), Postgres/SQLite (product data), analytics
(Plausible/Umami), search providers.

## Adding native tools (code)

For guardrailed actions (anything with caps/consent semantics), add a factory
in `nightshift/tools/` following `email_tools.py` as the pattern:

1. `@tool("name", "description the model reads", {"param": str})` on an async
   function returning `ok(...)`/`err(...)`.
2. Enforce limits via `Ledger` INSIDE the tool — never rely on the prompt.
3. Register it in `tools/__init__.py::build_company_mcp_server`.
4. Log every externally visible action to `outbox/`.

## Adding or tuning agents

Drop a markdown file into `prompts/agents/` — filename becomes the agent name:

```markdown
---
description: One line the CEO sees when deciding whom to delegate to.
---
System prompt for the specialist...
```

Ideas: `support` (dedicated inbox handling), `seo` (content strategy),
`analyst` (weekly deep-dives on kpis.csv).

## Tuning behavior per company

Best place: the company's own files — IDEA.md (strategy), VOICE.md (tone),
company.yaml (caps/budget/autonomy). The reflection loop tunes
`prompt_overrides/OVERRIDES.md` on its own; you can edit that file too — the
next reflection will respect your edits as the new baseline.

## Beyond nightly

`nightshift run <slug> --task "..."` is the on-demand escape hatch (Polsia's
"credits", except free). Wire it to anything: a Stream Deck button, a Slack
slash command, a phone shortcut over SSH.
