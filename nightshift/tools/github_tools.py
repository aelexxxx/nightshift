"""GitHub tools via the REST API. Repo content work (clone/commit/push) is done
by the agent with Bash + git; these tools cover account-level operations."""

from __future__ import annotations

import requests
from claude_agent_sdk import tool

from ..config import Company, Settings

API = "https://api.github.com"


def _headers(settings: Settings) -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def build_github_tools(settings: Settings, company: Company) -> list:
    from . import err, ok

    @tool(
        "create_repo",
        "Create a new GitHub repository under the configured account. Returns "
        "the clone URL. Use Bash+git afterwards to push code (the GITHUB_TOKEN "
        "env var is available in Bash; push via "
        "https://x-access-token:$GITHUB_TOKEN@github.com/<owner>/<repo>.git).",
        {"name": str, "description": str, "private": bool},
    )
    async def create_repo(args: dict) -> dict:
        name = str(args.get("name", "")).strip()
        if not name:
            return err("name is required.")
        try:
            r = requests.post(
                f"{API}/user/repos",
                headers=_headers(settings),
                json={
                    "name": name,
                    "description": str(args.get("description", "")),
                    "private": bool(args.get("private", False)),
                    "auto_init": True,
                },
                timeout=30,
            )
            if r.status_code >= 300:
                return err(f"GitHub API {r.status_code}: {r.text[:400]}")
            data = r.json()
            return ok(f"Repo created: {data.get('html_url')}\n"
                      f"clone_url: {data.get('clone_url')}")
        except Exception as e:  # noqa: BLE001
            return err(f"GitHub request failed: {e}")

    @tool(
        "create_issue",
        "Create an issue in a repo (format: owner/repo). Use issues as the "
        "engineering backlog so work survives between nightly runs.",
        {"repo": str, "title": str, "body": str},
    )
    async def create_issue(args: dict) -> dict:
        repo = str(args.get("repo", "")).strip()
        title = str(args.get("title", "")).strip()
        if "/" not in repo or not title:
            return err("repo must be 'owner/repo' and title is required.")
        try:
            r = requests.post(
                f"{API}/repos/{repo}/issues",
                headers=_headers(settings),
                json={"title": title, "body": str(args.get("body", ""))},
                timeout=30,
            )
            if r.status_code >= 300:
                return err(f"GitHub API {r.status_code}: {r.text[:400]}")
            return ok(f"Issue created: {r.json().get('html_url')}")
        except Exception as e:  # noqa: BLE001
            return err(f"GitHub request failed: {e}")

    @tool(
        "list_issues",
        "List open issues in a repo (format: owner/repo). Check this at the "
        "start of every run to pick up unfinished engineering work.",
        {"repo": str},
    )
    async def list_issues(args: dict) -> dict:
        repo = str(args.get("repo", "")).strip()
        if "/" not in repo:
            return err("repo must be 'owner/repo'.")
        try:
            r = requests.get(f"{API}/repos/{repo}/issues",
                             headers=_headers(settings),
                             params={"state": "open", "per_page": 30}, timeout=30)
            if r.status_code >= 300:
                return err(f"GitHub API {r.status_code}: {r.text[:400]}")
            issues = r.json()
            if not issues:
                return ok("No open issues.")
            lines = [f"#{i['number']}: {i['title']}" for i in issues if "pull_request" not in i]
            return ok("\n".join(lines) or "No open issues (only PRs).")
        except Exception as e:  # noqa: BLE001
            return err(f"GitHub request failed: {e}")

    return [create_repo, create_issue, list_issues]
