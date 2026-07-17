"""Configuration: global settings from .env + per-company settings from company.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPANIES_DIR = REPO_ROOT / "companies"
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_DIR = COMPANIES_DIR / "_template"


@dataclass
class Settings:
    """Global settings, loaded once from the repo-root .env file."""

    anthropic_api_key: str = ""
    claude_oauth_token: str = ""
    model: str = "claude-sonnet-4-5"
    owner_email: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    imap_host: str = "imap.gmail.com"
    imap_user: str = ""
    imap_password: str = ""

    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""

    github_token: str = ""
    github_user: str = ""

    run_at: str = "02:00"

    @property
    def has_model_auth(self) -> bool:
        return bool(self.anthropic_api_key or self.claude_oauth_token)

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def imap_configured(self) -> bool:
        return bool(self.imap_user and self.imap_password)

    @property
    def x_configured(self) -> bool:
        return all([self.x_api_key, self.x_api_secret,
                    self.x_access_token, self.x_access_token_secret])

    @property
    def github_configured(self) -> bool:
        return bool(self.github_token)


def load_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env")
    e = os.environ.get
    return Settings(
        anthropic_api_key=e("ANTHROPIC_API_KEY", ""),
        claude_oauth_token=e("CLAUDE_CODE_OAUTH_TOKEN", ""),
        model=e("NIGHTSHIFT_MODEL", "claude-sonnet-4-5"),
        owner_email=e("OWNER_EMAIL", ""),
        smtp_host=e("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(e("SMTP_PORT", "465")),
        smtp_user=e("SMTP_USER", ""),
        smtp_password=e("SMTP_PASSWORD", ""),
        imap_host=e("IMAP_HOST", "imap.gmail.com"),
        imap_user=e("IMAP_USER", "") or e("SMTP_USER", ""),
        imap_password=e("IMAP_PASSWORD", "") or e("SMTP_PASSWORD", ""),
        x_api_key=e("X_API_KEY", ""),
        x_api_secret=e("X_API_SECRET", ""),
        x_access_token=e("X_ACCESS_TOKEN", ""),
        x_access_token_secret=e("X_ACCESS_TOKEN_SECRET", ""),
        github_token=e("GITHUB_TOKEN", ""),
        github_user=e("GITHUB_USER", ""),
        run_at=e("NIGHTSHIFT_RUN_AT", "02:00"),
    )


@dataclass
class ChannelConfig:
    enabled: bool = False
    daily_cap: int = 0


@dataclass
class Company:
    """One business, backed by a directory under companies/."""

    slug: str
    path: Path
    name: str = ""
    mission: str = ""
    owner_email: str = ""
    model: str = ""                    # empty → global default
    max_turns: int = 150
    monthly_budget_usd: float = 50.0
    autonomy: str = "full"             # "full" | "draft"
    cold_outreach: bool = False
    kpis: list[str] = field(default_factory=list)
    skills: str | list[str] = "all"
    email: ChannelConfig = field(default_factory=ChannelConfig)
    twitter: ChannelConfig = field(default_factory=ChannelConfig)
    github: bool = False

    # Derived paths
    @property
    def workspace(self) -> Path:
        return self.path / "workspace"

    @property
    def memory(self) -> Path:
        return self.path / "memory"

    @property
    def journal(self) -> Path:
        return self.path / "journal"

    @property
    def outbox(self) -> Path:
        return self.path / "outbox"

    @property
    def overrides_file(self) -> Path:
        return self.path / "prompt_overrides" / "OVERRIDES.md"

    @property
    def paused(self) -> bool:
        return (self.path / "PAUSED").exists()


def load_company(path: Path) -> Company:
    """Load a company from its directory (must contain company.yaml)."""
    cfg_file = path / "company.yaml"
    if not cfg_file.exists():
        raise FileNotFoundError(f"{cfg_file} not found — not a company directory")
    raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}

    channels = raw.get("channels", {}) or {}
    em = channels.get("email", {}) or {}
    tw = channels.get("twitter", {}) or {}
    gh = channels.get("github", {}) or {}

    return Company(
        slug=path.name,
        path=path,
        name=raw.get("name", path.name),
        mission=raw.get("mission", "").strip(),
        owner_email=raw.get("owner_email", ""),
        model=raw.get("model", "") or "",
        max_turns=int(raw.get("max_turns", 150)),
        monthly_budget_usd=float(raw.get("monthly_budget_usd", 50)),
        autonomy=raw.get("autonomy", "full"),
        cold_outreach=bool(raw.get("cold_outreach", False)),
        kpis=list(raw.get("kpis", []) or []),
        skills=raw.get("skills", "all") or "all",
        email=ChannelConfig(
            enabled=bool(em.get("enabled", False)),
            daily_cap=int(em.get("daily_send_cap", 20)),
        ),
        twitter=ChannelConfig(
            enabled=bool(tw.get("enabled", False)),
            daily_cap=int(tw.get("daily_post_cap", 8)),
        ),
        github=bool(gh.get("enabled", False)) if isinstance(gh, dict) else bool(gh),
    )


def list_companies() -> list[Path]:
    """All company directories (skips the template and hidden dirs)."""
    if not COMPANIES_DIR.exists():
        return []
    return sorted(
        p for p in COMPANIES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "company.yaml").exists()
    )
