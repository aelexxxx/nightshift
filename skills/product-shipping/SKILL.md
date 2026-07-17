---
name: product-shipping
description: Scoping and shipping product increments as a nightly agent — cutting scope to one-night units, definition of done, tech choices a bot can maintain, and avoiding half-built graveyards.
---

# Product shipping

The engineering failure mode of autonomous companies isn't bad code — it's
graveyards of 60%-done features no single night could finish. Scope IS the
skill.

## One-night units

- Every task must be shippable in one run: deployed, tested, visible.
  Bigger ideas get sliced vertically (a working slice of the whole flow)
  never horizontally (all the models, no UI).
- Can't slice it into a night? Create GitHub issues for the slices, ship
  slice one tonight. The issue list is the only backlog that survives
  between runs — untracked intentions die at sunrise.
- The demo test: after tonight, could the owner click/see/use the result?
  If not, it wasn't a unit.

## Definition of done (all four, no exceptions)

1. Runs — you executed it (tests, or actually exercising the endpoint/page).
2. Deployed or committed+pushed — code that lives only in workspace/ is not
   real yet.
3. Observable — a KPI, log line, or page proves it works in reality.
4. Recorded — STATE.md updated (URLs, what exists), issue closed or updated.

"Should work", "just needs", "mostly done" are banned phrases; the honest
version is "not done, here's the issue link".

## Tech choices (boring on purpose)

- Default stack: static HTML/JS or a small Python/Node service, SQLite,
  plain files. One repo per product in workspace/.
- The maintainer is a nightly agent with a token budget: no k8s, no
  microservices, no framework-of-the-month, minimal dependencies (each dep
  is a future 2 a.m. breakage).
- Anything needing money or accounts (domain, hosting tier, DNS) →
  "Needs from you" with a concrete recommendation and cost.
- Secrets in env vars, never in code. Migrations reversible. Every repo has
  a README that lets next-night-you resume cold: how to run, deploy,
  where prod lives.

## Bug policy

- User-facing bugs from the inbox outrank feature work, always.
- Fix + a regression test in the same night, or an issue with reproduction
  steps if it can't land tonight.

## Weekly product hygiene

At the strategy review: close or explicitly kill stale issues (a wontfix
with a reason beats a zombie), check that deployed things still run (curl
the URLs), and delete dead experiments from the codebase — entropy is a tax
on every future night.
