"""Collect GitHub commit counts via search API across date ranges."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import date, timedelta

import requests


def get_token() -> str:
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    return result.stdout.strip()


def fetch_commit_count(start: date, end: date, token: str, retries: int = 3) -> int:
    """Return total commit count for the given date range (inclusive)."""
    url = "https://api.github.com/search/commits"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.cloak-preview+json",
    }
    q = f"committer-date:{start.isoformat()}..{end.isoformat()}"
    for attempt in range(retries):
        r = requests.get(url, headers=headers, params={"q": q, "per_page": 1}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data["total_count"]
        if r.status_code == 403:
            # Rate limited — wait and retry
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time() + 2, 5)
            print(f"  rate limited, sleeping {wait:.0f}s", flush=True)
            time.sleep(wait)
        else:
            print(f"  HTTP {r.status_code}: {r.text[:200]}", flush=True)
            time.sleep(5)
    raise RuntimeError(f"Failed after {retries} retries for {start}..{end}")


def month_ranges(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def week_ranges_for_month(year: int, month: int) -> list[tuple[date, date]]:
    start, end = month_ranges(year, month)
    weeks = []
    cur = start
    while cur <= end:
        wend = min(cur + timedelta(days=6), end)
        weeks.append((cur, wend))
        cur = wend + timedelta(days=1)
    return weeks


def main() -> None:
    token = get_token()
    results: list[dict] = []

    # --- Monthly data: Jan 2025 through June 2026 ---
    print("=== Monthly commit counts ===", flush=True)
    periods: list[tuple[int, int]] = []
    for m in range(1, 13):
        periods.append((2025, m))
    for m in range(1, 7):
        periods.append((2026, m))

    for year, month in periods:
        s, e = month_ranges(year, month)
        if e > date.today():
            e = date.today()
        if s > date.today():
            break
        count = fetch_commit_count(s, e, token)
        days = (e - s).days + 1
        per_week = count / days * 7
        print(f"  {year}-{month:02d}: {count:>12,}  ({per_week:>12,.0f}/week)", flush=True)
        results.append({"period": f"{year}-{month:02d}", "type": "month", "start": s.isoformat(),
                         "end": e.isoformat(), "count": count, "days": days})
        time.sleep(2.2)  # stay well under 30 req/min

    # --- Weekly drill-down for April and May 2026 (the claimed 275M/week period) ---
    print("\n=== Weekly drill-down: Apr–May 2026 ===", flush=True)
    for year, month in [(2026, 4), (2026, 5)]:
        for s, e in week_ranges_for_month(year, month):
            if e > date.today():
                e = date.today()
            if s > date.today():
                break
            count = fetch_commit_count(s, e, token)
            days = (e - s).days + 1
            per_week = count / days * 7
            print(f"  {s} – {e}: {count:>12,}  ({per_week:>12,.0f}/week equiv)", flush=True)
            results.append({"period": f"{s}_{e}", "type": "week", "start": s.isoformat(),
                             "end": e.isoformat(), "count": count, "days": days})
            time.sleep(2.2)

    # --- Annualized projections ---
    print("\n=== Summary ===", flush=True)
    months_2025 = [r for r in results if r["type"] == "month" and r["period"].startswith("2025")]
    total_2025 = sum(r["count"] for r in months_2025)
    print(f"  2025 total (Jan–Dec): {total_2025:>14,}")

    months_2026 = [r for r in results if r["type"] == "month" and r["period"].startswith("2026")]
    total_2026_ytd = sum(r["count"] for r in months_2026)
    days_2026 = sum(r["days"] for r in months_2026)
    annualized_2026 = total_2026_ytd / days_2026 * 365
    print(f"  2026 YTD total:       {total_2026_ytd:>14,}")
    print(f"  2026 annualized:      {annualized_2026:>14,.0f}")
    print(f"  YoY multiplier:       {annualized_2026 / total_2025:>14.1f}x")

    # Save raw data
    out = "commit_counts.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw data saved to {out}")


if __name__ == "__main__":
    main()
