"""
Cargo/crates.io Growth Analysis: Did Generative AI accelerate crate and version growth?

Tests two hypotheses:
  H1: New crate creation rate increased after the agentic coding explosion (Oct 2025)
  H2: Version release frequency increased after the agentic coding explosion (Oct 2025)

Statistical approach: Chow structural break test + segment linear regression
Data source: https://static.crates.io/db-dump.tar.gz (see fetch_data.py)
"""

from __future__ import annotations

import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from datetime import date

# ── Load data from CSVs ───────────────────────────────────────────────────────

def load_csv(path: str, col: str) -> tuple[list[date], list[int]]:
    months, values = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            months.append(date.fromisoformat(row["month"]))
            values.append(int(row[col]))
    return months, values

months_c, new_crates   = load_csv("data_new_crates_monthly.csv",  "new_crates")
months_v, new_versions = load_csv("data_versions_monthly.csv",    "new_versions")

assert months_c == months_v, "Month lists must match"
months = months_c

# Start from Jan 2018 to match the analysis window used in PyPI study
START = date(2018, 1, 1)
idx_start = next(i for i, m in enumerate(months) if m >= START)
months   = months[idx_start:]
new_crates   = new_crates[idx_start:]
new_versions = new_versions[idx_start:]

# ── Numeric time index (months since Jan 2018) ────────────────────────────────

t = np.array([(m.year - 2018) * 12 + m.month for m in months], dtype=float)
y_c = np.array(new_crates,   dtype=float)
y_v = np.array(new_versions, dtype=float)

# ── Outlier flagging ──────────────────────────────────────────────────────────

KNOWN_ANOMALIES: dict[tuple[int, int], str] = {}

anomaly_mask = np.array([
    (m.year, m.month) in KNOWN_ANOMALIES for m in months
])

# ── Helper: linear regression ─────────────────────────────────────────────────

def linreg(x, y):
    slope, intercept, r, p, se = stats.linregress(x, y)
    return slope, intercept, r**2, p

def rss(x, y, slope, intercept):
    return np.sum((y - (intercept + slope * x))**2)

# ── Chow structural break test ────────────────────────────────────────────────

BREAK_MONTH = (2025 - 2018) * 12 + 10  # Oct 2025

def chow_test(t, y, break_t, label):
    mask1, mask2 = t <= break_t, t > break_t
    t1, y1 = t[mask1], y[mask1]
    t2, y2 = t[mask2], y[mask2]

    s1, i1, r1, _ = linreg(t1, y1)
    s2, i2, r2, _ = linreg(t2, y2)
    s_all, i_all, _, _ = linreg(t, y)

    rss1       = rss(t1, y1, s1, i1)
    rss2       = rss(t2, y2, s2, i2)
    rss_pooled = rss(t, y, s_all, i_all)

    k = 2
    n = len(t)
    F_stat  = ((rss_pooled - rss1 - rss2) / k) / ((rss1 + rss2) / (n - 2 * k))
    p_value = 1 - stats.f.cdf(F_stat, dfn=k, dfd=n - 2 * k)
    pct_change = (s2 - s1) / abs(s1) * 100 if s1 != 0 else float("inf")

    return F_stat, p_value, {
        "label": label,
        "n_pre": len(t1), "n_post": len(t2),
        "slope_pre": s1, "r2_pre": r1,
        "slope_post": s2, "r2_post": r2,
        "intercept_pre": i1, "intercept_post": i2,
        "F": F_stat, "p": p_value,
        "slope_change_pct": pct_change,
    }

t_clean   = t[~anomaly_mask]
y_c_clean = y_c[~anomaly_mask]
y_v_clean = y_v[~anomaly_mask]

chow_c = chow_test(t_clean, y_c_clean, BREAK_MONTH, "New crates")
chow_v = chow_test(t_clean, y_v_clean, BREAK_MONTH, "New versions")

# ── Print statistical results ─────────────────────────────────────────────────

print("=" * 70)
print("Cargo/crates.io Growth Analysis — Chow test, break: Oct 2025")
print("=" * 70)

for F, p, d in (chow_c, chow_v):
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    print(f"\n{d['label']}  (n_pre={d['n_pre']}, n_post={d['n_post']})")
    print(f"  Pre  slope: {d['slope_pre']:+.1f}/month  R²={d['r2_pre']:.3f}")
    print(f"  Post slope: {d['slope_post']:+.1f}/month  R²={d['r2_post']:.3f}  (change {d['slope_change_pct']:+.0f}%)")
    print(f"  F(2,{d['n_pre']+d['n_post']-4}) = {F:.2f},  p = {p:.2e}  {sig}")

# ── Plotting ──────────────────────────────────────────────────────────────────

BREAK_DATE  = date(2022, 11, 1)  # ChatGPT launch
AGENTS_DATE = date(2025, 10, 1)  # Agentic explosion
ANNO_COLOR  = "#cc3333"

def plot_raw(ax, values, ylabel, chow_result):
    from matplotlib.ticker import FuncFormatter
    F, p, d = chow_result
    normal = ~anomaly_mask
    ax.plot(months, values, color="#aaaaaa", linewidth=0.8, zorder=1)
    ax.scatter(
        [m for m, ok in zip(months, normal) if ok],
        [v for v, ok in zip(values, normal) if ok],
        s=14, color="#444444", zorder=3,
    )
    if anomaly_mask.any():
        ax.scatter(
            [m for m, ok in zip(months, anomaly_mask) if ok],
            [v for v, ok in zip(values, anomaly_mask) if ok],
            s=40, marker="x", linewidths=1.5, color=ANNO_COLOR, zorder=4,
            label="Anomaly",
        )

    # Regression lines
    t_pre  = t_clean[t_clean <= BREAK_MONTH]
    t_post = t_clean[t_clean >  BREAK_MONTH]

    def t_to_date(tv):
        yr  = 2018 + int((tv - 1) // 12)
        mo  = int((tv - 1) % 12) + 1
        return date(yr, mo, 1)

    if len(t_pre) > 1:
        dates_pre = [t_to_date(ti) for ti in [t_pre[0], t_pre[-1]]]
        vals_pre  = [d["intercept_pre"] + d["slope_pre"] * ti for ti in [t_pre[0], t_pre[-1]]]
        ax.plot(dates_pre, vals_pre, color="#2ecc71", linewidth=1.5,
                linestyle="-", zorder=5, label=f'Pre trend (slope {d["slope_pre"]:+.0f}/mo)')
    if len(t_post) > 1:
        dates_post = [t_to_date(ti) for ti in [t_post[0], t_post[-1]]]
        vals_post  = [d["intercept_post"] + d["slope_post"] * ti for ti in [t_post[0], t_post[-1]]]
        ax.plot(dates_post, vals_post, color="#e67e22", linewidth=1.5,
                linestyle="-", zorder=5, label=f'Post trend (slope {d["slope_post"]:+.0f}/mo)')

    ymax = max(values) * 1.08
    ax.axvline(BREAK_DATE,  color="#c0392b", linestyle="--", linewidth=1.2, alpha=0.85)
    ax.axvline(AGENTS_DATE, color="#8e44ad", linestyle="--", linewidth=1.2, alpha=0.85)
    ax.text(BREAK_DATE,  ymax * 0.97, "ChatGPT\nlaunch",    fontsize=8, color="#c0392b", ha="left",  va="top")
    ax.text(AGENTS_DATE, ymax * 0.97, "Agentic\nexplosion", fontsize=8, color="#8e44ad", ha="right", va="top")
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    ax.text(0.02, 0.06, f"Chow F={F:.1f}, p={p:.1e} {sig}", transform=ax.transAxes,
            fontsize=8, va="bottom", color="#333333")
    ax.set_xlim(months[0], months[-1])
    ax.set_ylim(0, ymax)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.legend(fontsize=7.5, loc="upper left")

date_label = months[-1].strftime("%b %Y")

fig_c, ax_c = plt.subplots(figsize=(7, 5))
fig_c.suptitle(f"Cargo/crates.io — New crates per month (Jan 2018 – {date_label})",
               fontsize=11, fontweight="bold")
plot_raw(ax_c, new_crates, "New crates / month", chow_c)
fig_c.tight_layout()
fig_c.savefig("cargo_growth_crates.png", dpi=150, bbox_inches="tight")
print("\nSaved: cargo_growth_crates.png")

fig_v, ax_v = plt.subplots(figsize=(7, 5))
fig_v.suptitle(f"Cargo/crates.io — New versions per month (Jan 2018 – {date_label})",
               fontsize=11, fontweight="bold")
plot_raw(ax_v, new_versions, "New versions / month", chow_v)
fig_v.tight_layout()
fig_v.savefig("cargo_growth_versions.png", dpi=150, bbox_inches="tight")
print("Saved: cargo_growth_versions.png")

# ── Month-over-month growth, last 12 months ───────────────────────────────────

mom_c = [(months[i], (y_c[i] - y_c[i-1]) / y_c[i-1] * 100) for i in range(1, len(months))]
mom_v = [(months[i], (y_v[i] - y_v[i-1]) / y_v[i-1] * 100) for i in range(1, len(months))]

last12_c = mom_c[-12:]
last12_v = mom_v[-12:]

fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
start_mo = last12_c[0][0].strftime("%b %Y")
end_mo   = last12_c[-1][0].strftime("%b %Y")
fig3.suptitle(
    f"Month-over-Month Growth — Last 12 Months ({start_mo} – {end_mo})",
    fontsize=13, fontweight="bold"
)

def bar_mom(ax, data, title):
    dates  = [d for d, _ in data]
    values = [v for _, v in data]
    colors = ["#e05c00" if v >= 0 else "#888888" for v in values]
    bars = ax.bar(range(len(dates)), values, color=colors, edgecolor="white", width=0.7)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels([d.strftime("%b\n%Y") for d in dates], fontsize=8)
    ax.set_ylabel("MoM change (%)")
    ax.set_title(title, fontsize=11)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + (0.5 if v >= 0 else -1.2),
            f"{v:+.1f}%", ha="center", va="bottom", fontsize=7.5,
        )
    ax.set_ylim(min(values) - 5, max(values) + 7)

bar_mom(ax1, last12_c, "New crates / month")
bar_mom(ax2, last12_v, "New versions / month")

plt.tight_layout()
plt.savefig("cargo_mom_last12.png", dpi=150, bbox_inches="tight")
print("Saved: cargo_mom_last12.png")

# ── Save MoM CSV ──────────────────────────────────────────────────────────────

with open("data_mom_last12.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["month", "mom_pct_new_crates", "mom_pct_new_versions"])
    for c, v in zip(last12_c, last12_v):
        w.writerow([c[0].isoformat(), round(c[1], 4), round(v[1], 4)])
print("Saved: data_mom_last12.csv")

# ── Baseline growth (2018–2022, pre-ChatGPT) ──────────────────────────────────

def annual_totals(months, values):
    by_year: dict[int, list[int]] = {}
    for m, v in zip(months, values):
        by_year.setdefault(m.year, []).append(v)
    return {y: sum(vs) for y, vs in by_year.items() if len(vs) == 12}

crate_annual   = annual_totals(months, new_crates)
version_annual = annual_totals(months, new_versions)

baseline_years = [y for y in range(2018, 2023) if y in crate_annual and y in version_annual]
if len(baseline_years) >= 2:
    c_yoy = [(crate_annual[y]   - crate_annual[y-1])   / crate_annual[y-1]   * 100 for y in baseline_years[1:]]
    v_yoy = [(version_annual[y] - version_annual[y-1]) / version_annual[y-1] * 100 for y in baseline_years[1:]]
    c_cagr = (crate_annual[baseline_years[-1]]   / crate_annual[baseline_years[0]])   ** (1 / (len(baseline_years)-1)) - 1
    v_cagr = (version_annual[baseline_years[-1]] / version_annual[baseline_years[0]]) ** (1 / (len(baseline_years)-1)) - 1
    print(f"\n5-year baseline ({baseline_years[0]}–{baseline_years[-1]}):")
    print(f"  New crates   YoY: {[f'{r:.1f}%' for r in c_yoy]}  avg={sum(c_yoy)/len(c_yoy):.1f}%  CAGR={c_cagr*100:.1f}%")
    print(f"  New versions YoY: {[f'{r:.1f}%' for r in v_yoy]}  avg={sum(v_yoy)/len(v_yoy):.1f}%  CAGR={v_cagr*100:.1f}%")
