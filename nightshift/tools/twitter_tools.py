"""X / Twitter tools via the official API v2 (free tier friendly).

Free tier limits are tight (roughly 500 posts/month at the time of writing);
the daily cap in company.yaml keeps you well inside them.
"""

from __future__ import annotations

from datetime import datetime

from claude_agent_sdk import tool

from ..config import Company, Settings
from ..ledger import Ledger


def _client(settings: Settings):
    import tweepy
    return tweepy.Client(
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        access_token=settings.x_access_token,
        access_token_secret=settings.x_access_token_secret,
    )


def _log_post(company: Company, kind: str, text: str, url: str = "") -> None:
    d = company.outbox / "posted"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    (d / f"{stamp}_{kind}.md").write_text(f"{url}\n\n{text}\n", encoding="utf-8")


def build_twitter_tools(settings: Settings, company: Company, ledger: Ledger) -> list:
    from . import err, ok

    @tool(
        "post_tweet",
        "Post a single tweet to the company X account. Max 280 chars. A daily "
        "post cap applies; in 'draft' autonomy mode the tweet is queued for "
        "human approval instead. Write in the brand voice from memory/VOICE.md — "
        "never generic filler.",
        {"text": str},
    )
    async def post_tweet(args: dict) -> dict:
        text = str(args.get("text", "")).strip()
        if not text:
            return err("text is required.")
        if len(text) > 280:
            return err(f"Tweet is {len(text)} chars (max 280). Shorten it.")
        allowed, detail = ledger.can_use("twitter")
        if not allowed:
            return err(detail)
        if company.autonomy == "draft":
            _log_post(company, "pending_tweet", text)
            return ok("Autonomy mode is 'draft': tweet queued for human approval. "
                      "It has NOT been posted.")
        try:
            resp = _client(settings).create_tweet(text=text)
            tweet_id = resp.data.get("id", "")
        except Exception as e:  # noqa: BLE001
            return err(f"X API failure: {e}")
        ledger.record_use("twitter")
        url = f"https://x.com/i/web/status/{tweet_id}"
        _log_post(company, "tweet", text, url)
        _, detail = ledger.can_use("twitter")
        return ok(f"Posted: {url}. Daily usage: {detail}.")

    @tool(
        "post_thread",
        "Post a thread to the company X account. Separate tweets with a line "
        "containing only '---'. Each part max 280 chars. The whole thread "
        "counts against the daily cap (one unit per tweet).",
        {"text": str},
    )
    async def post_thread(args: dict) -> dict:
        raw = str(args.get("text", "")).strip()
        parts = [p.strip() for p in raw.split("\n---\n") if p.strip()]
        if len(parts) < 2:
            return err("A thread needs at least 2 parts separated by a '---' line.")
        for i, p in enumerate(parts, 1):
            if len(p) > 280:
                return err(f"Part {i} is {len(p)} chars (max 280).")
        cap = ledger.cap_for("twitter")
        if ledger.used_today("twitter") + len(parts) > cap:
            return err(f"Thread of {len(parts)} tweets would exceed the daily cap "
                       f"({ledger.used_today('twitter')}/{cap} used).")
        if company.autonomy == "draft":
            _log_post(company, "pending_thread", raw)
            return ok("Autonomy mode is 'draft': thread queued for human approval. "
                      "It has NOT been posted.")
        try:
            client = _client(settings)
            reply_to = None
            first_id = None
            for p in parts:
                resp = client.create_tweet(text=p, in_reply_to_tweet_id=reply_to)
                reply_to = resp.data.get("id")
                first_id = first_id or reply_to
                ledger.record_use("twitter")
        except Exception as e:  # noqa: BLE001
            return err(f"X API failure mid-thread (some parts may be live): {e}")
        url = f"https://x.com/i/web/status/{first_id}"
        _log_post(company, "thread", raw, url)
        return ok(f"Thread of {len(parts)} tweets posted: {url}")

    return [post_tweet, post_thread]
