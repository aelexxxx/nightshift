"""Scheduler daemon: runs every company once per night at NIGHTSHIFT_RUN_AT,
staggered 20 minutes apart. Prefer cron (scripts/cron.example) on servers;
the daemon is the zero-setup alternative."""

from __future__ import annotations

import asyncio
import traceback
from datetime import date, datetime, timedelta

from . import reporting
from .config import Settings, list_companies, load_company
from .engine import run_night

STAGGER_MIN = 20
POLL_SECONDS = 30


def _target_time(settings: Settings, index: int, day: date) -> datetime:
    hour, minute = (int(x) for x in settings.run_at.split(":"))
    return (datetime.combine(day, datetime.min.time())
            .replace(hour=hour, minute=minute)
            + timedelta(minutes=STAGGER_MIN * index))


async def daemon(settings: Settings) -> None:
    print(f"nightshift daemon started — nightly runs at {settings.run_at}, "
          f"{STAGGER_MIN} min stagger. Ctrl-C to stop.")
    done: set[tuple[str, str]] = set()

    while True:
        now = datetime.now()
        for index, path in enumerate(list_companies()):
            slug = path.name
            key = (slug, date.today().isoformat())
            if key in done:
                continue
            target = _target_time(settings, index, date.today())
            if now < target:
                continue
            done.add(key)
            print(f"[{now:%H:%M}] starting nightly run: {slug}")
            try:
                meta = await run_night(path, settings)
                print(f"[{datetime.now():%H:%M}] finished {slug}: {meta}")
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                try:
                    reporting.send_alert(settings, load_company(path),
                                         f"Nightly run crashed: {e}\n\n"
                                         f"{traceback.format_exc()[-3000:]}")
                except Exception:  # noqa: BLE001
                    pass
        # Forget yesterday's completions
        today = date.today().isoformat()
        done = {k for k in done if k[1] == today}
        await asyncio.sleep(POLL_SECONDS)
