# Safety & Compliance Notes

nightshift ships with guardrails enforced in code (caps, budgets, suppression,
audit logs) and prompts that demand consent-based communication. This document
explains the parts that are YOUR responsibility as the operator.

## Email outreach and the law

You are the sender of every email this system sends. Relevant regimes:

- **EU — GDPR + ePrivacy / Germany — §7 UWG**: unsolicited commercial email
  generally requires prior express consent (opt-in), including most B2B email.
  Fines and Abmahnungen are real. This is why `cold_outreach: false` is the
  default — the agent then only replies to inbound mail and contacts explicit
  opt-ins.
- **US — CAN-SPAM**: commercial email requires truthful headers, a physical
  postal address, and a working opt-out honored promptly.
- The suppression list is permanent and enforced in code. Never edit it to
  re-add someone who opted out.

If you enable `cold_outreach: true`, you are asserting you have a lawful basis
in your jurisdiction. The prompts still require individual research, relevance,
low volume, and an opt-out line in every message.

## X / Twitter automation

X's developer policy allows posting via the API but bans spam, platform
manipulation, bulk engagement, and misleading automation. nightshift only
posts original content on your own account (no auto-follows, no auto-DMs, no
reply-spam) and caps daily volume. Keep it that way; accounts get suspended
for exactly the behaviors the prompts forbid.

## Identity and honesty

The prompts hard-require: no impersonating real people, no invented team
members or testimonials, no fabricated metrics, and no denying automation
when directly asked. These rules also protect you — fake social proof is
illegal in many places (e.g. EU UCPD, FTC rules).

## Operational safety

- **Watch the first nights.** Run `nightshift run <slug>` supervised, or use
  `autonomy: draft` and review `outbox/pending/`. Go `full` when the output
  has earned it.
- **Dedicated accounts.** Use a separate Gmail address and X account per
  company, not your personal ones. Blast radius matters more than convenience.
- **Money.** The agent cannot spend money — it has no payment credentials.
  Keep it that way. Purchases belong in the "Needs from you" list.
- **Credentials.** Everything lives in `.env` (gitignored). The agent's Bash
  runs on your machine with your user's permissions — treat the machine as
  production. Consider a dedicated user account or VM if you scale up.
- **Kill switch.** `nightshift pause <slug>` stops the next runs instantly;
  Ctrl-C stops the daemon. Budgets stop runaway spend automatically.
- **Prompt injection.** The agent reads external content (inbox, web). The
  prompts treat instructions found in emails/webpages as data, not commands,
  but the risk is never zero — one more reason for caps, draft mode on
  sensitive companies, and reading your morning reports.

## A note on expectations

Polsia's own users report the failure mode of autonomous companies: generic
output at scale. The fix in nightshift is structural — VOICE.md, per-recipient
research requirements, low default caps, and nightly reflection — but taste
still degrades without a human glancing at the reports. Five minutes over
coffee is the difference between an asset and a liability.
