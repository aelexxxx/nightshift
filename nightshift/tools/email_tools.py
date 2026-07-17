"""Email tools: send (SMTP), read inbox (IMAP), manage suppression list."""

from __future__ import annotations

import email as email_lib
import imaplib
import smtplib
from datetime import datetime
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr

from claude_agent_sdk import tool

from ..config import Company, Settings
from ..ledger import Ledger


def _outbox_record(company: Company, folder: str, to: str, subject: str, body: str) -> str:
    d = company.outbox / folder
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = d / f"{stamp}_{to.replace('@', '_at_')}.md"
    path.write_text(f"To: {to}\nSubject: {subject}\nDate: {stamp}\n\n{body}\n",
                    encoding="utf-8")
    return str(path)


def smtp_send(settings: Settings, to: str, subject: str, body: str,
              html: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as s:
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def _body_snippet(msg, limit: int = 800) -> str:
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True) or b""
                    return payload.decode(part.get_content_charset() or "utf-8",
                                          "replace")[:limit]
            return "(no text part)"
        payload = msg.get_payload(decode=True) or b""
        return payload.decode(msg.get_content_charset() or "utf-8", "replace")[:limit]
    except Exception as e:  # noqa: BLE001
        return f"(could not decode body: {e})"


def build_email_tools(settings: Settings, company: Company, ledger: Ledger) -> list:
    from . import err, ok

    @tool(
        "send_email",
        "Send an email from the company address. Guardrails: recipients on the "
        "suppression list are refused; a daily send cap applies; in 'draft' "
        "autonomy mode the email is queued for human approval instead of sent. "
        "Every send is logged to the outbox for auditing.",
        {"to": str, "subject": str, "body": str},
    )
    async def send_email(args: dict) -> dict:
        to = str(args.get("to", "")).strip()
        subject = str(args.get("subject", "")).strip()
        body = str(args.get("body", ""))
        if not (to and subject and body):
            return err("to, subject and body are all required.")
        if "@" not in parseaddr(to)[1]:
            return err(f"'{to}' is not a valid email address.")
        if ledger.suppressed(to):
            return err(f"{to} is on the suppression list (opted out). Do not contact.")
        allowed, detail = ledger.can_use("email")
        if not allowed:
            return err(detail)
        if company.autonomy == "draft":
            path = _outbox_record(company, "pending", to, subject, body)
            return ok(f"Autonomy mode is 'draft': email queued for human approval "
                      f"at {path}. It has NOT been sent.")
        try:
            smtp_send(settings, to, subject, body)
        except Exception as e:  # noqa: BLE001
            return err(f"SMTP failure: {e}")
        ledger.record_use("email")
        _outbox_record(company, "sent", to, subject, body)
        _, detail = ledger.can_use("email")
        return ok(f"Email sent to {to}. Daily usage: {detail}.")

    @tool(
        "check_inbox",
        "Read the most recent messages from the company inbox (IMAP). Returns "
        "sender, subject, date and a plain-text snippet for each. Use it to "
        "triage replies, support requests, and opt-out requests. If someone "
        "asks to stop receiving email, call suppress_email immediately.",
        {"limit": int, "unseen_only": bool},
    )
    async def check_inbox(args: dict) -> dict:
        if not settings.imap_configured:
            return err("IMAP is not configured (.env).")
        limit = min(int(args.get("limit", 10) or 10), 30)
        unseen_only = bool(args.get("unseen_only", False))
        try:
            with imaplib.IMAP4_SSL(settings.imap_host) as m:
                m.login(settings.imap_user, settings.imap_password)
                m.select("INBOX", readonly=True)
                criteria = "UNSEEN" if unseen_only else "ALL"
                _, data = m.search(None, criteria)
                ids = data[0].split()
                if not ids:
                    return ok("Inbox: no matching messages.")
                lines = []
                for mid in reversed(ids[-limit:]):
                    _, msg_data = m.fetch(mid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)
                    lines.append(
                        f"--- id={mid.decode()} ---\n"
                        f"From: {_decode(msg.get('From'))}\n"
                        f"Subject: {_decode(msg.get('Subject'))}\n"
                        f"Date: {msg.get('Date')}\n"
                        f"Snippet: {_body_snippet(msg)}\n"
                    )
                return ok("\n".join(lines))
        except Exception as e:  # noqa: BLE001
            return err(f"IMAP failure: {e}")

    @tool(
        "suppress_email",
        "Add an address to the permanent suppression list. MUST be called for "
        "every unsubscribe/opt-out request. Suppressed addresses can never be "
        "emailed again.",
        {"address": str, "reason": str},
    )
    async def suppress_email(args: dict) -> dict:
        address = str(args.get("address", "")).strip()
        if "@" not in address:
            return err(f"'{address}' is not a valid email address.")
        ledger.suppress(address, str(args.get("reason", "")))
        return ok(f"{address} permanently suppressed.")

    return [send_email, check_inbox, suppress_email]
