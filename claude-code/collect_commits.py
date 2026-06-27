#!/usr/bin/env python3
"""
Collect GitHub commit counts attributed to Claude Code.
Phase 1: monthly totals Jun 2025–Jun 2026 (13 queries)
Phase 2: daily March 2026 to verify the claimed 326K single-day peak (31 queries)

Attribution proxy: commit messages containing "noreply@anthropic.com"
(the Co-Authored-By email Claude Code injects).
"""
from __future__ import annotations

import csv
import json
import subprocess
import time
from datetime import date, timedelta
import calendar

DELAY = 10.0  # generous; secondary limit is burst-based


def gh_search(date_from: str, date_to: str, retries: int = 3) -> int:
    q = f"noreply@anthropic.com committer-date:{date_from}..{date_to}"
    for attempt in range(retries):
        r = subprocess.run(
            ["gh", "api", f"search/commits?q={q}&per_page=1",
             "-H", "Accept: application/vnd.github.cloak-preview"],
            capture_output=True, text=True,
        )
        try:
            data = json.loads(r.stdout)
            if "total_count" in data:
                return data["total_count"]
            backoff = 120 * (attempt + 1)
            print(f"    rate limited, sleeping {backoff}s (attempt {attempt+1}/{retries})")
            time.sleep(backoff)
        except Exception as e:
            print(f"    parse error: {e} | stdout: {r.stdout[:100]}")
            time.sleep(30)
    return -1


def write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def phase1_monthly() -> list[dict]:
    print("=== Phase 1: monthly totals (Jun 2025 – Jun 2026) ===")
    months = [
        (2025, 6), (2025, 7), (2025, 8), (2025, 9), (2025, 10), (2025, 11),
        (2025, 12), (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5), (2026, 6),
    ]
    rows = []
    for y, m in months:
        first = date(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        last = date(y, m, min(last_day, 25 if (y == 2026 and m == 6) else last_day))
        count = gh_search(first.isoformat(), last.isoformat())
        row = {"month": f"{y}-{m:02d}", "date_from": first.isoformat(),
               "date_to": last.isoformat(), "count": count}
        rows.append(row)
        print(f"  {row['month']}: {count:>8,}")
        write_csv("monthly_claude_commits.csv", rows,
                  ["month", "date_from", "date_to", "count"])
        time.sleep(DELAY)
    return rows


def phase2_march_daily() -> list[dict]:
    print("\n=== Phase 2: March 2026 daily ===")
    rows = []
    current = date(2026, 3, 1)
    end = date(2026, 3, 31)
    while current <= end:
        d = current.isoformat()
        count = gh_search(d, d)
        row = {"date": d, "count": count}
        rows.append(row)
        print(f"  {d}: {count:>8,}")
        write_csv("march2026_daily_claude_commits.csv", rows, ["date", "count"])
        time.sleep(DELAY)
        current += timedelta(days=1)
    return rows


def main():
    monthly = phase1_monthly()
    march = phase2_march_daily()

    print("\n=== Results ===")

    valid_m = [(r["month"], r["count"]) for r in monthly if r["count"] >= 0]
    if valid_m:
        peak_m = max(valid_m, key=lambda x: x[1])
        total = sum(c for _, c in valid_m)
        print(f"Monthly peak: {peak_m[0]} → {peak_m[1]:,}")
        print(f"12-month total: {total:,}")

    valid_d = [(r["date"], r["count"]) for r in march if r["count"] >= 0]
    if valid_d:
        peak_d = max(valid_d, key=lambda x: x[1])
        print(f"\nMarch 2026 peak day: {peak_d[0]} → {peak_d[1]:,}")
        print(f"Claimed peak:        326,731")
        ratio = peak_d[1] / 326731 if peak_d[1] > 0 else 0
        print(f"Ratio actual/claimed: {ratio:.2%}")


if __name__ == "__main__":
    main()
