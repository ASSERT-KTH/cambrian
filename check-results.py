#!/usr/bin/env python3
"""
Verifies that all numerical results cited in README.md are reproducible
from analyze.py output and the data CSV files.

Usage: python3 check-results.py
Exit code 0 = all consistent, 1 = inconsistencies found.
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

# ── Run analyze.py and collect its output ─────────────────────────────────────

proc = subprocess.run(['python3', 'analyze.py'], capture_output=True, text=True)
if proc.returncode != 0:
    print("ERROR: analyze.py failed")
    print(proc.stderr)
    sys.exit(1)

output = proc.stdout

# ── Build reference set: all numbers from output + CSV files ──────────────────

def extract_numbers_from_text(text):
    """Extract numbers from free text (e.g. analyze.py stdout)."""
    nums = set()
    for m in re.finditer(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?', text):
        try:
            nums.add(float(m.group()))
        except ValueError:
            pass
    return nums

def extract_numbers_from_csvs():
    """Parse data CSVs properly and return all numeric cell values."""
    nums = set()
    for path in Path('.').glob('data_*.csv'):
        for row in csv.reader(path.read_text().splitlines()):
            for cell in row:
                try:
                    nums.add(float(cell))
                except ValueError:
                    pass
    return nums

reference = extract_numbers_from_text(output) | extract_numbers_from_csvs()

# ── Explicit checks: (description, expected_value, absolute_tolerance) ────────
# Values come from README.md; tolerance accounts for rounding in the text.
# Numbers sourced only from external BigQuery queries (median, p99, active
# package counts) are noted but not checked here.

checks = [
    # Chow test — new packages (from Chow table in README)
    ("n_pre months",                          89,       0),
    ("n_post months",                          6,       0),
    ("pre slope, new packages (/mo)",         89.9,     0.5),
    ("R² pre, new packages",                  0.854,    0.001),
    ("post slope, new packages (/mo)",      2822.2,     1.0),
    ("R² post, new packages",                 0.932,    0.001),
    ("slope change, new packages (%)",       3040,      5),
    ("F-statistic, new packages",             167.89,   0.1),

    # Chow test — releases
    ("pre slope, releases (/mo)",            3658.8,    1.0),
    ("R² pre, releases",                      0.975,    0.001),
    ("post slope, releases (/mo)",          59910.5,   10.0),
    ("R² post, releases",                     0.901,    0.001),
    ("slope change, releases (%)",           1537,       5),
    ("F-statistic, releases",                 210.44,    0.1),

    # 5-year baseline (2018–2022)
    ("CAGR new packages, 2018–2022 (%)",      28.8,     0.1),
    ("CAGR releases, 2018–2022 (%)",          42.6,     0.1),

    # Nov comparison table — new packages (from data CSVs)
    ("2018-11 new packages",                  3333,     0),
    ("2021-11 new packages",                  7416,     0),
    ("2024-11 new packages",                  9660,     0),
    ("2025-11 new packages",                 12972,     0),
    ("2026-02 new packages",                 20055,     0),
    ("2026-03 new packages",                 25651,     0),
    ("2026-04 new packages",                 24996,     0),

    # Nov comparison table — releases (from data CSVs)
    ("2018-11 releases",                     53432,     0),
    ("2021-11 releases",                    168956,     0),
    ("2024-11 releases",                    306096,     0),
    ("2025-11 releases",                    387431,     0),
    ("2026-02 releases",                    500102,     0),
    ("2026-03 releases",                    647395,     0),
    ("2026-04 releases",                    639282,     0),
]

# Not checked (sourced from a separate BigQuery query, not analyze.py):
#   median releases/package/year = 4  (2018, 2024, 2025)
#   p99 releases/package/year: 77 (2018), 260 (2024)
#   active packages: ~63k (2018), ~224k (2025)

# ── Run checks ────────────────────────────────────────────────────────────────

failures = []
for desc, expected, tol in checks:
    found = any(abs(expected - r) <= max(tol, 1e-9) for r in reference)
    if not found:
        failures.append((desc, expected))

print(f"Checked {len(checks)} numerical claims from README.md.")

if failures:
    print(f"\n{len(failures)} INCONSISTENC{'Y' if len(failures)==1 else 'IES'} FOUND:\n")
    for desc, val in failures:
        print(f"  FAIL  {desc}: {val}")
    sys.exit(1)
else:
    print("All checks passed — README.md is consistent with analyze.py.")
