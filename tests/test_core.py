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

    def test_selfopt_json_extraction(self):
        from nightshift.selfopt import _extract_json
        fenced = 'text\n```json\n{"grade": 7, "lessons": ["x"]}\n```\nmore'
        self.assertEqual(_extract_json(fenced)["grade"], 7)
        bare = 'noise {"grade": 5, "summary": "ok", "lessons": [], "overrides_md": ""} tail'
        self.assertEqual(_extract_json(bare)["grade"], 5)
        self.assertEqual(_extract_json("no json here"), {})


if __name__ == "__main__":
    unittest.main()
