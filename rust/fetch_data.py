"""
Fetch crates.io monthly stats from the public database dump.
Produces:
  data_new_crates_monthly.csv
  data_versions_monthly.csv
"""

from __future__ import annotations

import csv
import os
import tarfile
import urllib.request
from collections import defaultdict
from datetime import date

DUMP_URL = "https://static.crates.io/db-dump.tar.gz"
DUMP_FILE = "db-dump.tar.gz"

csv.field_size_limit(10_000_000)


def download_dump():
    if os.path.exists(DUMP_FILE):
        print(f"Using cached {DUMP_FILE}")
        return
    print(f"Downloading {DUMP_URL} …")
    urllib.request.urlretrieve(DUMP_URL, DUMP_FILE)
    print(f"Saved {DUMP_FILE} ({os.path.getsize(DUMP_FILE) // 1_000_000} MB)")


def extract_file(name_suffix: str, dest: str):
    if os.path.exists(dest):
        print(f"Using cached {dest}")
        return
    print(f"Extracting {name_suffix} from archive …")
    with tarfile.open(DUMP_FILE, "r:gz") as tf:
        for member in tf.getmembers():
            if member.name.endswith(name_suffix):
                f = tf.extractfile(member)
                if f:
                    with open(dest, "wb") as out:
                        while True:
                            chunk = f.read(1 << 20)
                            if not chunk:
                                break
                            out.write(chunk)
                    print(f"  Saved {dest} ({os.path.getsize(dest) // 1_000_000} MB)")
                    return
    raise FileNotFoundError(f"{name_suffix} not found in dump")


def month_key(ts: str) -> date | None:
    try:
        y, m = int(ts[:4]), int(ts[5:7])
        return date(y, m, 1)
    except Exception:
        return None


def count_by_month(path: str, date_col: str, skip_yanked: bool = False) -> dict[date, int]:
    counts: dict[date, int] = defaultdict(int)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if skip_yanked and row.get("yanked", "f") == "t":
                continue
            mk = month_key(row.get(date_col, ""))
            if mk:
                counts[mk] += 1
    return counts


def main():
    download_dump()

    extract_file("crates.csv", "crates_raw.csv")
    extract_file("versions.csv", "versions_raw.csv")

    print("Counting new crates per month …")
    new_crates = count_by_month("crates_raw.csv", "created_at")
    print(f"  {sum(new_crates.values()):,} total crates across {len(new_crates)} months")

    print("Counting new (non-yanked) versions per month …")
    new_versions = count_by_month("versions_raw.csv", "created_at", skip_yanked=True)
    print(f"  {sum(new_versions.values()):,} total versions across {len(new_versions)} months")

    # Align and trim to complete months only
    all_months = sorted(set(new_crates) | set(new_versions))
    today = date.today()
    current_month = date(today.year, today.month, 1)
    all_months = [m for m in all_months if m < current_month]

    with open("data_new_crates_monthly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "new_crates"])
        for m in all_months:
            w.writerow([m.isoformat(), new_crates.get(m, 0)])
    print("Saved data_new_crates_monthly.csv")

    with open("data_versions_monthly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "new_versions"])
        for m in all_months:
            w.writerow([m.isoformat(), new_versions.get(m, 0)])
    print("Saved data_versions_monthly.csv")

    print("\nLast 6 months:")
    print(f"  {'month':<12}  {'new_crates':>12}  {'new_versions':>13}")
    for m in all_months[-6:]:
        print(f"  {m.isoformat():<12}  {new_crates.get(m,0):>12,}  {new_versions.get(m,0):>13,}")


if __name__ == "__main__":
    main()
