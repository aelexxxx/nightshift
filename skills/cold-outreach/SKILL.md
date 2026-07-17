---
name: cold-outreach
description: Consent-aware outbound email — research, personalization, deliverability, and follow-up discipline. Required reading before any outreach; also covers replying to inbound.
---

# Outreach & inbound email

Reputation compounds and never resets. One spammy blast can burn the domain,
the brand, and the legal position simultaneously. Volume is never the lever;
relevance is.

## Hard rules (mirror the code-level guardrails)

- `cold_outreach: false` → only inbound, existing contacts, explicit opt-ins.
- Every recipient individually researched. If you can't say in one sentence
  why THIS person benefits THIS week, you don't send.
- No two identical emails. Templates are for structure, never for sentences.
- Marketing/outreach mails always contain a working opt-out line. Any opt-out
  → suppress_email immediately.
- Stay far below the daily cap when reply rates are low: outreach that isn't
  answered is a signal to fix the message, not raise the volume.

## Anatomy of a cold email that gets answered

- **Subject**: 2–5 plain words about *their* thing, not yours. Lowercase
  reads personal. Never clickbait, never "quick question" (burned).
- **Line 1**: proof you actually looked — reference something specific and
  recent they made/said/shipped. Generic flattery is deleted on sight.
- **Line 2–3**: the bridge — the problem you solve, stated in their context,
  with one concrete specific (number, example, artifact).
- **Ask**: ONE small, low-friction ask ("worth a look?", "want the 2-min
  demo?"). Never "hop on a call" in email #1.
- **Length**: under 90 words. It should look typed on a phone. Plain text,
  no images, no links until they reply (deliverability + trust).
- Sign-off with a real name and the opt-out line.
- Then run the copywriting de-AI pass — cold inboxes have the best-trained
  AI detectors on earth: actual humans deleting fast.

## Follow-up discipline

- Max 2 follow-ups, 3–5 days apart, each adding NEW value (a resource, a
  concrete observation) — never "just bumping this".
- No reply after 3 touches = closed-lost. Log it in PIPELINE.md, move on.

## Inbound (outranks all outreach)

- Reply within one run, always. Helpful first, selling second.
- Match their energy and length. Short question → short answer.
- Angry or disappointed → acknowledge plainly, fix what's fixable, no
  corporate non-apologies. Escalate to the owner if reputational.
- Every inbound conversation gets a PIPELINE.md entry with a next step.

## Deliverability basics

- Warm domains slowly: single digits per day for the first weeks.
- Watch bounces — 2 bounces in a batch = stop, verify the list.
- Never buy lists. Ever.
- Sending address must have SPF/DKIM set up (escalate to owner if not — it's
  a "Needs from you").

## Metrics that matter

sent → opened (if trackable) → replied → conversation → conversion. Log
honestly via log_kpi. Reply rate < 3% on researched outreach = the message
is wrong; run an experiment on the first line, not on volume.
