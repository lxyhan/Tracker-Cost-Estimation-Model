"""
Within-domain byte distribution for eight representative tracker domains.

Each row is one tracker domain; horizontal box shows IQR, whiskers extend
to p1--p99. Log x-axis. % of zero responses (beacons) annotated to the
right.

Output: anrw-submission/figures/fig_within_domain_examples.pdf
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV  = ROOT / "data" / "raw" / "05_per_request_full" / "per_request_full.csv"
OUT  = ROOT / "anrw-submission" / "figures" / "fig_within_domain_examples.pdf"

COLOR_BOX     = "#1f6feb"
COLOR_WHISKER = "#9aa6b4"

DOMAINS = [
    "googleads.g.doubleclick.net",
    "platform.twitter.com",
    "pagead2.googlesyndication.com",
    "tpc.googlesyndication.com",
    "www.google-analytics.com",
]

bytes_by = {d: [] for d in DOMAINS}
for chunk in pd.read_csv(CSV, usecols=["tracker_domain", "transfer_bytes"],
                          chunksize=500_000):
    for d in DOMAINS:
        bytes_by[d].extend(chunk.loc[chunk["tracker_domain"] == d,
                                     "transfer_bytes"].to_numpy().tolist())

stats = []
for d in DOMAINS:
    arr = np.asarray(bytes_by[d])
    nonzero = arr[arr > 0]
    stats.append({
        "domain":   d,
        "pct_zero": (arr == 0).mean() * 100,
        "p1":       np.quantile(nonzero, 0.01),
        "p25":      np.quantile(nonzero, 0.25),
        "p50":      np.quantile(nonzero, 0.50),
        "p75":      np.quantile(nonzero, 0.75),
        "p99":      np.quantile(nonzero, 0.99),
    })

short_label = {
    "googleads.g.doubleclick.net":   "googleads.doubleclick.net",
    "platform.twitter.com":          "platform.twitter.com",
    "pagead2.googlesyndication.com": "pagead2.googlesynd.com",
    "tpc.googlesyndication.com":     "tpc.googlesynd.com",
    "www.google-analytics.com":      "google-analytics.com",
}

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(5.5, 2.4))

y = np.arange(len(stats))
h = 0.55
xmin, xmax = 1, 1e7

for yi, s in enumerate(stats):
    ax.plot([s["p1"], s["p99"]], [yi, yi],
            color=COLOR_WHISKER, linewidth=1.4, solid_capstyle="butt", zorder=1)
    for cap_x in (s["p1"], s["p99"]):
        ax.plot([cap_x, cap_x], [yi - h * 0.30, yi + h * 0.30],
                color=COLOR_WHISKER, linewidth=1.4, zorder=1)
    rect = mpatches.Rectangle((s["p25"], yi - h/2), s["p75"] - s["p25"], h,
                              facecolor=COLOR_BOX, edgecolor="white",
                              linewidth=0.6, zorder=2)
    ax.add_patch(rect)
    ax.plot([s["p50"], s["p50"]], [yi - h/2, yi + h/2],
            color="white", linewidth=2.0, zorder=3)
    ax.text(xmax * 1.10, yi, f"{s['pct_zero']:.0f}% zero",
            va="center", fontsize=8, color="#444")

ax.set_yticks(y)
ax.set_yticklabels([short_label[s["domain"]] for s in stats])
ax.invert_yaxis()
ax.set_xscale("log")
ax.set_xlim(xmin, xmax)
ax.set_xlabel("Transfer bytes per request  (log scale)")

from matplotlib.ticker import FuncFormatter
def byte_fmt(x, _):
    if x < 1: return ""
    if x < 1024: return f"{int(x)} B"
    if x < 1024 ** 2: return f"{int(x / 1024)} KB"
    return f"{int(x / 1024 / 1024)} MB"
ax.xaxis.set_major_formatter(FuncFormatter(byte_fmt))

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color("#888")
ax.spines["bottom"].set_color("#888")
ax.tick_params(colors="#444", length=3)
ax.grid(axis="x", alpha=0.20, linestyle="-", linewidth=0.7)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
