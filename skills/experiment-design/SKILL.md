---
name: experiment-design
description: How to run growth/product experiments as an agent — hypothesis format, one-variable discipline, kill criteria, and the EXPERIMENTS.md ledger that makes the goal loop work.
---

# Experiment design

The goal loop only improves if changes are treated as experiments with
predictions, not as vibes. This is the discipline layer between "goals"
(what must become true) and "nightly actions" (what you do about it).

## The ledger: memory/EXPERIMENTS.md

Every experiment gets an entry BEFORE it starts:

```
## EXP-007: Shorter cold-email opener
- Goal it serves: 20 replies/month (goals.yaml)
- Hypothesis: referencing the recipient's latest post in line 1 lifts
  reply rate from 4% to 8%+
- Change: exactly one variable — the opener; everything else frozen
- Sample/duration: 40 sends or 14 days, whichever first
- Kill criteria: <2% replies after 20 sends → stop early
- Status: running (started 2026-07-12)
- Result: (filled at close) — measured numbers, verdict, lesson
```

## Rules

1. **One variable.** Change the headline AND the price AND the audience and
   you learn nothing. Freeze everything else and say so in the entry.
2. **Prediction before data.** Write the expected number down first —
   that's what makes the result informative either way.
3. **Pre-committed sample/duration and kill criteria.** No peeking-and-
   stopping when the numbers look good after 5 data points; no zombie
   experiments running forever. When the threshold hits, close it and write
   the verdict.
4. **Max 2–3 experiments running at once** per company; they must not share
   a variable (don't test two landing-page changes simultaneously).
5. **Close honestly.** "No effect" and "made it worse" are results — often
   the most valuable ones. The verdict goes into LESSONS.md; if it changes
   standing behavior, the reflection pass encodes it into overrides.
6. **Sample-size sanity.** Below ~30 observations per arm, call it a signal,
   not proof — fine for cheap decisions, not for irreversible ones (see
   standards: reversible decisions get made fast, irreversible ones
   escalate).

## Choosing what to test (at the weekly review)

Score candidate experiments ICE: Impact on the lagging goal × Confidence ×
Ease. Run the top 1–2. Priority heuristic: fix the leakiest funnel stage
first — no traffic → launch/SEO experiments; traffic but no signups →
landing page; signups but no activation → product/onboarding; activation
but no revenue → pricing.

## The loop, end to end

goals.yaml defines the target → weekly review picks experiments against the
lagging goal → nightly runs execute them → log_kpi records outcomes →
EXPERIMENTS.md closes with verdicts → reflection turns verdicts into
overrides → next week starts smarter. If any link is missing (no entry, no
numbers, no verdict), the loop is broken — fixing that outranks running new
experiments.
