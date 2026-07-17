---
name: analytics-kpis
description: Designing and reading KPIs for a tiny company — picking the few numbers that matter, funnel thinking, honest measurement with kpis.csv, and avoiding vanity-metric theater.
---

# Analytics & KPIs

You can't steer what you don't measure, and you'll steer wrong if you
measure theater. This company's entire analytics stack is kpis.csv + honest
logging — that's a feature: every number has a name attached (yours).

## Designing the KPI set (few, layered)

- **North star (1)**: the number that best proxies delivered value —
  usually paying customers, MRR, or weekly active users. Lives in
  goals.yaml.
- **Funnel (3–5)**: the stages that lead there, e.g.
  visits → signups → activated → paying → retained. Instrument the ones you
  can actually observe; mark the rest as blind spots in STATE.md.
- **Input metrics (2–4)**: what YOU control each night — posts published,
  outreach sent, pages shipped, experiments closed. Inputs are graded on
  consistency, outputs on trend.

Anti-pattern: 15 metrics logged, none looked at. If a metric hasn't changed
a decision in 3 weeks, stop logging it (note why in LESSONS.md).

## Honest measurement rules

- Log with log_kpi every run, same names, consistent units (`revenue_usd`,
  not sometimes `revenue`). The name IS the schema.
- Never estimate a number you can look up; never log a number you can't
  source. Unknown → don't log, list as blind spot instead.
- Zeroes are data. Logging `signups=0` nightly is what makes the first
  `signups=1` meaningful.
- Distinguish cumulative vs. per-period explicitly in the note field.
- Blind spots are engineering tasks: no visit counting → ship a
  privacy-friendly counter (Plausible/Umami or a 20-line logger); no revenue
  visibility → connect the Stripe MCP (escalate to owner).

## Reading the numbers (weekly review)

- Trends over points: compare this week's median to last week's, not last
  night to the night before. With tiny numbers, ratios lie — "signups
  doubled" from 1 to 2 is noise; say "1 → 2".
- Find the leakiest funnel stage (worst week-over-week conversion) — that's
  where next week's experiments aim (experiment-design skill).
- Correlation caution at n<30: "posted more, got more signups" is a
  hypothesis to test, not a conclusion to encode.
- Every weekly review answers three questions in the journal: What moved?
  What did we do that plausibly moved it? What's the cheapest test of that
  belief?

## Reporting to the owner

Morning reports show deltas with baselines ("signups 3 this week, 1 last
week"), never percentages on tiny bases, and always flag data quality issues
before conclusions. Bad news travels first.
