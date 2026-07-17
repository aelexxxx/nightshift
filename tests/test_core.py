"""Fast unit tests for the guardrail layer and config parsing (no SDK, no network).

Run:  python -m pytest tests/  (or: python -m unittest tests.test_core)
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nightshift.config import load_company  # noqa: E402
from nightshift.ledger import Ledger  # noqa: E402

COMPANY_YAML = """
name: Test Co
mission: >
  Test mission
max_turns: 42
monthly_budget_usd: 10
autonomy: draft
cold_outreach: false
channels:
  email:
    enabled: true
    daily_send_cap: 2
  twitter:
    enabled: true
    daily_post_cap: 3
  github:
    enabled: true
kpis:
  - signups
"""


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "company.yaml").write_text(COMPANY_YAML, encoding="utf-8")
        self.company = load_company(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_company_parsing(self):
        c = self.company
        self.assertEqual(c.name, "Test Co")
        self.assertEqual(c.max_turns, 42)
        self.assertEqual(c.monthly_budget_usd, 10)
        self.assertEqual(c.autonomy, "draft")
        self.assertTrue(c.email.enabled)
        self.assertEqual(c.email.daily_cap, 2)
        self.assertEqual(c.twitter.daily_cap, 3)
        self.assertTrue(c.github)
        self.assertFalse(c.cold_outreach)
        self.assertFalse(c.paused)

    def test_budget(self):
        ledger = Ledger(self.company)
        self.assertTrue(ledger.budget_ok())
        ledger.record_cost(9.5)
        self.assertTrue(ledger.budget_ok())
        ledger.record_cost(1.0)
        self.assertFalse(ledger.budget_ok())
        # Persisted?
        self.assertAlmostEqual(Ledger(self.company).month_spend(), 10.5)

    def test_daily_caps(self):
        ledger = Ledger(self.company)
        ok, _ = ledger.can_use("email")
        self.assertTrue(ok)
        ledger.record_use("email")
        ledger.record_use("email")
        ok, msg = ledger.can_use("email")
        self.assertFalse(ok)
        self.assertIn("cap", msg.lower())
        ok, _ = ledger.can_use("twitter")  # independent channel
        self.assertTrue(ok)

    def test_suppression(self):
        ledger = Ledger(self.company)
        self.assertFalse(ledger.suppressed("a@b.com"))
        ledger.suppress("A@B.com", "asked to stop")
        self.assertTrue(ledger.suppressed("a@b.com"))
        self.assertTrue(ledger.suppressed(" A@B.COM "))

    def test_pause_flag(self):
        (self.dir / "PAUSED").touch()
        self.assertTrue(load_company(self.dir).paused)

    def test_goals_progress(self):
        from nightshift.goals import goals_block, is_review_day, latest_kpis
        (self.dir / "goals.yaml").write_text(
            "north_star: first customer\nreview_day: sunday\ngoals:\n"
            "  - {metric: signups, target: 50, by: 2099-01-01}\n"
            "  - {metric: revenue_usd, target: 100, by: 2099-01-01}\n",
            encoding="utf-8")
        (self.dir / "kpis.csv").write_text(
            "date,name,value,note\n2026-07-01,signups,5,\n"
            "2026-07-16,signups,12,\n", encoding="utf-8")
        kpis = latest_kpis(self.company)
        self.assertEqual(kpis["signups"][0], 12.0)
        block = goals_block(self.company)
        self.assertIn("signups: 12 / 50", block)
        self.assertIn("NO DATA YET", block)          # revenue_usd
        self.assertIn("north star", block.lower())
        import datetime
        sunday = datetime.date(2026, 7, 19)
        monday = datetime.date(2026, 7, 20)
        self.assertTrue(is_review_day(self.company, sunday))
        self.assertFalse(is_review_day(self.company, monday))

    def test_goals_absent(self):
        from nightshift.goals import goals_block, is_review_day
        self.assertEqual(goals_block(self.company), "")
        self.assertFalse(is_review_day(self.company))

    def test_skills_loading(self):
        from nightshift.skills import index_block, load_skills
        skills = load_skills("all")
        names = {s.name for s in skills}
        self.assertIn("copywriting", names)
        self.assertGreaterEqual(len(skills), 10)
        subset = load_skills(["copywriting", "pricing"])
        self.assertEqual({s.name for s in subset}, {"copywriting", "pricing"})
        block = index_block(subset)
        self.assertIn("copywriting", block)
        self.assertIn("SKILL.md", block)
        self.assertEqual(index_block([]), "")

    def test_company_skills_field(self):
        (self.dir / "company.yaml").write_text(
            COMPANY_YAML + "skills: [copywriting, launch]\n", encoding="utf-8")
        c = load_company(self.dir)
        self.assertEqual(c.skills, ["copywriting", "launch"])
        self.assertEqual(self.company.skills, "all")  # default

    def test_selfopt_json_extraction(self):
        from nightshift.selfopt import _extract_json
        fenced = 'text\n```json\n{"grade": 7, "lessons": ["x"]}\n```\nmore'
        self.assertEqual(_extract_json(fenced)["grade"], 7)
        bare = 'noise {"grade": 5, "summary": "ok", "lessons": [], "overrides_md": ""} tail'
        self.assertEqual(_extract_json(bare)["grade"], 5)
        self.assertEqual(_extract_json("no json here"), {})


if __name__ == "__main__":
    unittest.main()
