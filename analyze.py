"""
PyPI Growth Analysis: Did Generative AI accelerate package and release growth?

Tests two hypotheses:
  H1: New package creation rate increased after ChatGPT launch (Nov 2022)
  H2: Release frequency increased after ChatGPT launch (Nov 2022)

Statistical approach: Chow structural break test + segment linear regression
"""

import csv
import io
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from datetime import date

# ── Raw data ──────────────────────────────────────────────────────────────────

NEW_PKG_CSV = """\
month,new_packages
2018-01-01,2713
2018-02-01,2593
2018-03-01,3083
2018-04-01,3343
2018-05-01,3006
2018-06-01,2880
2018-07-01,4092
2018-08-01,3196
2018-09-01,2973
2018-10-01,3440
2018-11-01,3333
2018-12-01,3003
2019-01-01,3369
2019-02-01,3473
2019-03-01,4020
2019-04-01,3745
2019-05-01,3931
2019-06-01,3696
2019-07-01,4400
2019-08-01,4026
2019-09-01,3926
2019-10-01,4215
2019-11-01,4380
2019-12-01,4170
2020-01-01,4833
2020-02-01,4738
2020-03-01,5166
2020-04-01,5842
2020-05-01,6401
2020-06-01,6545
2020-07-01,10809
2020-08-01,6381
2020-09-01,6354
2020-10-01,6348
2020-11-01,6550
2020-12-01,6835
2021-01-01,7105
2021-02-01,12846
2021-03-01,20409
2021-04-01,7543
2021-05-01,8334
2021-06-01,6866
2021-07-01,7745
2021-08-01,7072
2021-09-01,6710
2021-10-01,7106
2021-11-01,7416
2021-12-01,8125
2022-01-01,8509
2022-02-01,9593
2022-03-01,9653
2022-04-01,8969
2022-05-01,7497
2022-06-01,7371
2022-07-01,7204
2022-08-01,10714
2022-09-01,7524
2022-10-01,9483
2022-11-01,9376
2022-12-01,7597
2023-01-01,8961
2023-02-01,23704
2023-03-01,9300
2023-04-01,8713
2023-05-01,8865
2023-06-01,8113
2023-07-01,8058
2023-08-01,8052
2023-09-01,7596
2023-10-01,7694
2023-11-01,7782
2023-12-01,7190
2024-01-01,8245
2024-02-01,8463
2024-03-01,9276
2024-04-01,8358
2024-05-01,11706
2024-06-01,8072
2024-07-01,8848
2024-08-01,8179
2024-09-01,8169
2024-10-01,9371
2024-11-01,9660
2024-12-01,8616
2025-01-01,9410
2025-02-01,8753
2025-03-01,13253
2025-04-01,12140
2025-05-01,11852
2025-06-01,12679
2025-07-01,12258
2025-08-01,11288
2025-09-01,11878
2025-10-01,12028
2025-11-01,12972
2025-12-01,13987
2026-01-01,16391
2026-02-01,20055
2026-03-01,25651
2026-04-01,24996
"""

RELEASES_CSV = """\
month,releases
2018-01-01,36877
2018-02-01,36415
2018-03-01,43124
2018-04-01,45792
2018-05-01,42535
2018-06-01,46522
2018-07-01,46949
2018-08-01,49438
2018-09-01,46310
2018-10-01,54585
2018-11-01,53432
2018-12-01,48501
2019-01-01,57788
2019-02-01,56838
2019-03-01,62683
2019-04-01,66437
2019-05-01,66416
2019-06-01,61662
2019-07-01,72752
2019-08-01,71660
2019-09-01,71899
2019-10-01,78498
2019-11-01,84346
2019-12-01,80833
2020-01-01,88714
2020-02-01,89748
2020-03-01,105380
2020-04-01,117246
2020-05-01,122616
2020-06-01,130217
2020-07-01,143727
2020-08-01,127424
2020-09-01,134082
2020-10-01,140453
2020-11-01,134685
2020-12-01,142970
2021-01-01,148300
2021-02-01,156819
2021-03-01,190841
2021-04-01,165025
2021-05-01,170268
2021-06-01,157846
2021-07-01,155799
2021-08-01,158727
2021-09-01,158261
2021-10-01,170932
2021-11-01,168956
2021-12-01,164534
2022-01-01,175265
2022-02-01,165837
2022-03-01,192095
2022-04-01,180602
2022-05-01,188733
2022-06-01,184606
2022-07-01,184476
2022-08-01,204545
2022-09-01,191943
2022-10-01,202974
2022-11-01,211170
2022-12-01,194316
2023-01-01,227349
2023-02-01,249532
2023-03-01,265265
2023-04-01,240612
2023-05-01,248328
2023-06-01,242750
2023-07-01,248381
2023-08-01,269722
2023-09-01,264275
2023-10-01,291030
2023-11-01,276878
2023-12-01,251570
2024-01-01,268878
2024-02-01,275060
2024-03-01,295714
2024-04-01,278106
2024-05-01,280792
2024-06-01,278977
2024-07-01,282373
2024-08-01,286399
2024-09-01,274765
2024-10-01,331240
2024-11-01,306096
2024-12-01,284253
2025-01-01,318534
2025-02-01,314769
2025-03-01,366994
2025-04-01,354334
2025-05-01,364756
2025-06-01,360433
2025-07-01,368862
2025-08-01,352075
2025-09-01,378336
2025-10-01,395090
2025-11-01,387431
2025-12-01,386935
2026-01-01,443871
2026-02-01,500102
2026-03-01,647395
2026-04-01,639282
"""

# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text.strip()))
    rows = list(reader)
    months = [date.fromisoformat(r['month']) for r in rows]
    values = [int(list(r.values())[1]) for r in rows]
    return months, values

months_pkg, new_packages = parse_csv(NEW_PKG_CSV)
months_rel, releases = parse_csv(RELEASES_CSV)

assert months_pkg == months_rel, "Month lists must match"
months = months_pkg

# Convert months to numeric index (months since Jan 2018)
t = np.array([(m.year - 2018) * 12 + m.month for m in months], dtype=float)
y_pkg = np.array(new_packages, dtype=float)
y_rel = np.array(releases, dtype=float)

# ── Outlier flagging ──────────────────────────────────────────────────────────
# Known spikes likely driven by spam/typosquatting campaigns, not organic growth.
# We identify months whose value is > 2.5 IQR above the rolling window median.

KNOWN_ANOMALIES = {
    # (year, month): reason
    (2020, 7): "spam campaign",
    (2021, 2): "spam campaign",
    (2021, 3): "spam campaign (peak)",
    (2022, 8): "spam campaign",
    (2023, 2): "spam campaign (peak)",
}

anomaly_mask = np.array([
    (m.year, m.month) in KNOWN_ANOMALIES for m in months
])

# ── Helper: linear regression & residuals ────────────────────────────────────

def linreg(x, y):
    slope, intercept, r, p, se = stats.linregress(x, y)
    return slope, intercept, r**2, p

def rss(x, y, slope, intercept):
    resid = y - (intercept + slope * x)
    return np.sum(resid**2)

# ── Chow structural break test ────────────────────────────────────────────────
# Break date: October 2025 (agentic explosion)
BREAK_MONTH = (2025 - 2018) * 12 + 10  # t value for Oct 2025

def chow_test(t, y, break_t, label):
    """
    Chow test for a structural break at break_t.
    k = 2 parameters (slope + intercept); F ~ F(2, n-4).
    """
    mask1 = t <= break_t
    mask2 = t > break_t

    t1, y1 = t[mask1], y[mask1]
    t2, y2 = t[mask2], y[mask2]

    s1, i1, r1, _ = linreg(t1, y1)
    s2, i2, r2, _ = linreg(t2, y2)
    s_all, i_all, _, _ = linreg(t, y)

    rss1 = rss(t1, y1, s1, i1)
    rss2 = rss(t2, y2, s2, i2)
    rss_pooled = rss(t, y, s_all, i_all)

    k = 2
    n = len(t)
    n1, n2 = len(t1), len(t2)

    F_stat = ((rss_pooled - rss1 - rss2) / k) / ((rss1 + rss2) / (n - 2 * k))
    p_value = 1 - stats.f.cdf(F_stat, dfn=k, dfd=n - 2 * k)
    pct_change = (s2 - s1) / abs(s1) * 100 if s1 != 0 else float('inf')

    return F_stat, p_value, {
        'label': label,
        'n_pre': n1, 'n_post': n2,
        'slope_pre': s1, 'r2_pre': r1,
        'slope_post': s2, 'r2_post': r2,
        'F': F_stat, 'p': p_value,
        'slope_change_pct': pct_change,
    }

t_clean = t[~anomaly_mask]
y_pkg_clean = y_pkg[~anomaly_mask]
y_rel_clean = y_rel[~anomaly_mask]

chow_pkg = chow_test(t_clean, y_pkg_clean, BREAK_MONTH, 'New packages')
chow_rel = chow_test(t_clean, y_rel_clean, BREAK_MONTH, 'Total releases')

# ── Print statistical results ─────────────────────────────────────────────────

print("=" * 70)
print("PyPI Growth Analysis — Chow test, break: Oct 2025")
print("=" * 70)

for F, p, d in (chow_pkg, chow_rel):
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    print(f"\n{d['label']}  (n_pre={d['n_pre']}, n_post={d['n_post']})")
    print(f"  Pre  slope: {d['slope_pre']:+.1f}/month  R²={d['r2_pre']:.3f}")
    print(f"  Post slope: {d['slope_post']:+.1f}/month  R²={d['r2_post']:.3f}  (change {d['slope_change_pct']:+.0f}%)")
    print(f"  F(2,{d['n_pre']+d['n_post']-4}) = {F:.2f},  p = {p:.2e}  {sig}")

# ── Plotting ──────────────────────────────────────────────────────────────────

BREAK_DATE  = date(2022, 11, 1)
AGENTS_DATE = date(2025, 10, 1)
ANNO_COLOR  = '#cc3333'

fig, (ax_pkg, ax_rel) = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('PyPI Monthly Growth (Jan 2018 – Apr 2026)', fontsize=13, fontweight='bold')

def plot_raw(ax, values, ylabel, title):
    from matplotlib.ticker import FuncFormatter
    normal = ~anomaly_mask
    ax.plot(months, values, color='#aaaaaa', linewidth=0.8, zorder=1)
    ax.scatter([m for m, ok in zip(months, normal) if ok],
               [v for v, ok in zip(values, normal) if ok],
               s=14, color='#444444', zorder=3)
    ax.scatter([m for m, ok in zip(months, anomaly_mask) if ok],
               [v for v, ok in zip(values, anomaly_mask) if ok],
               s=40, marker='x', linewidths=1.5, color=ANNO_COLOR, zorder=4,
               label='Spam/bot campaign')
    ymax = max(values) * 1.08
    ax.axvline(BREAK_DATE,  color='#c0392b', linestyle='--', linewidth=1.2, alpha=0.85)
    ax.axvline(AGENTS_DATE, color='#8e44ad', linestyle='--', linewidth=1.2, alpha=0.85)
    ax.text(BREAK_DATE,  ymax * 0.97, 'ChatGPT\nlaunch',    fontsize=8, color='#c0392b', ha='left', va='top')
    ax.text(AGENTS_DATE, ymax * 0.97, 'Agentic\nexplosion', fontsize=8, color='#8e44ad', ha='left', va='top')
    ax.set_xlim(months[0], months[-1])
    ax.set_ylim(0, ymax)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
    ax.tick_params(axis='x', rotation=30, labelsize=8)
    ax.legend(fontsize=8, loc='upper left')

plot_raw(ax_pkg, new_packages, 'New packages / month', 'New packages per month')
plot_raw(ax_rel, releases,     'Releases / month',     'Total releases per month')

plt.tight_layout()
plt.savefig('pypi_growth.png', dpi=150, bbox_inches='tight')
print("\nSaved: pypi_growth.png")

# ── Month-over-month growth, last 12 months ───────────────────────────────────

# Compute MoM % change for each series
mom_pkg = [(months[i], (y_pkg[i] - y_pkg[i-1]) / y_pkg[i-1] * 100)
           for i in range(1, len(months))]
mom_rel = [(months[i], (y_rel[i] - y_rel[i-1]) / y_rel[i-1] * 100)
           for i in range(1, len(months))]

# Keep last 12 months
last12_pkg = mom_pkg[-12:]
last12_rel = mom_rel[-12:]

fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig3.suptitle('Month-over-Month Growth — Last 12 Months (May 2025 – Apr 2026)',
              fontsize=13, fontweight='bold')

def bar_mom(ax, data, title):
    dates  = [d for d, _ in data]
    values = [v for _, v in data]
    colors = ['#e05c00' if v >= 0 else '#888888' for v in values]
    bars = ax.bar(range(len(dates)), values, color=colors, edgecolor='white', width=0.7)
    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels([d.strftime('%b\n%Y') for d in dates], fontsize=8)
    ax.set_ylabel('MoM change (%)')
    ax.set_title(title, fontsize=11)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                v + (0.5 if v >= 0 else -1.2),
                f'{v:+.1f}%', ha='center', va='bottom', fontsize=7.5)
    ax.set_ylim(min(values) - 5, max(values) + 7)

bar_mom(ax1, last12_pkg, 'New packages / month')
bar_mom(ax2, last12_rel, 'Total releases / month')

plt.tight_layout()
plt.savefig('pypi_mom_last12.png', dpi=150, bbox_inches='tight')
print("Saved: pypi_mom_last12.png")

# ── Save data CSVs ────────────────────────────────────────────────────────────

import csv as _csv

def write_csv(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = _csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

write_csv('data_new_packages_monthly.csv',
          ['month', 'new_packages', 'outlier'],
          [(m.isoformat(), v, int(a))
           for m, v, a in zip(months, new_packages, anomaly_mask)])

write_csv('data_releases_monthly.csv',
          ['month', 'releases', 'outlier'],
          [(m.isoformat(), v, int(a))
           for m, v, a in zip(months, releases, anomaly_mask)])

write_csv('data_mom_last12.csv',
          ['month', 'mom_pct_new_packages', 'mom_pct_releases'],
          [(p[0].isoformat(), round(p[1], 4), round(r[1], 4))
           for p, r in zip(last12_pkg, last12_rel)])

print("Saved: data_new_packages_monthly.csv")
print("Saved: data_releases_monthly.csv")
print("Saved: data_mom_last12.csv")

# ── 5-year baseline growth (2018–2022, pre-ChatGPT) ──────────────────────────

def annual_totals(months, values):
    by_year = {}
    for m, v in zip(months, values):
        by_year.setdefault(m.year, []).append(v)
    return {y: sum(v) for y, v in by_year.items() if len(v) == 12}

pkg_annual = annual_totals(months, new_packages)
rel_annual = annual_totals(months, releases)

baseline_years = [2018, 2019, 2020, 2021, 2022]
pkg_yoy_rates = [(pkg_annual[y] - pkg_annual[y-1]) / pkg_annual[y-1] * 100
                 for y in baseline_years[1:]]
rel_yoy_rates = [(rel_annual[y] - rel_annual[y-1]) / rel_annual[y-1] * 100
                 for y in baseline_years[1:]]

pkg_cagr = (pkg_annual[2022] / pkg_annual[2018]) ** (1/4) - 1
rel_cagr = (rel_annual[2022] / rel_annual[2018]) ** (1/4) - 1

print(f"\n5-year baseline (2018–2022):")
print(f"  New packages YoY: {[f'{r:.1f}%' for r in pkg_yoy_rates]}  avg={sum(pkg_yoy_rates)/len(pkg_yoy_rates):.1f}%  CAGR={pkg_cagr*100:.1f}%")
print(f"  Releases YoY:     {[f'{r:.1f}%' for r in rel_yoy_rates]}  avg={sum(rel_yoy_rates)/len(rel_yoy_rates):.1f}%  CAGR={rel_cagr*100:.1f}%")

