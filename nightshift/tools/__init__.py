"""Assembles the in-process MCP server exposing nightshift's channel tools.

Every tool is built via a factory that closes over (settings, company, ledger),
so guardrails (caps, budget, suppression, autonomy mode) are enforced in code —
not by prompt goodwill.
"""

from __future__ import annotations

from claude_agent_sdk import create_sdk_mcp_server

from ..config import Company, Settings
from ..ledger import Ledger
from .email_tools import build_email_tools
from .github_tools import build_github_tools
from .ledger_tools import build_ledger_tools
from .twitter_tools import build_twitter_tools


def build_company_mcp_server(settings: Settings, company: Company, ledger: Ledger):
    """Return an SDK MCP server named 'company' with all enabled tools."""
    tools = []
    tools += build_ledger_tools(company, ledger)
    if company.email.enabled and settings.email_configured:
        tools += build_email_tools(settings, company, ledger)
    if company.twitter.enabled and settings.x_configured:
        tools += build_twitter_tools(settings, company, ledger)
    if company.github and settings.github_configured:
        tools += build_github_tools(settings, company)
    return create_sdk_mcp_server(name="company", version="1.0.0", tools=tools)


def ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def err(text: str) -> dict:
    return {"content": [{"type": "text", "text": f"ERROR: {text}"}]}
