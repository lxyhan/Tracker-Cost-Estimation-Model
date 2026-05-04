"""
Target distribution: visualizes why squared-error fails and Tweedie loss is
the right choice. Shows the 39.5% spike at zero (beacons) and the heavy
right tail extending to 8.6 MB on a log-scale x axis.

Reads transfer_bytes from data/raw/05_per_request_full/per_request_full.csv
in chunks (the file is 514 MB).

Output: anrw-submission/figures/fig_target_dist.pdf
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "raw" / "05_per_request_full" / "per_request_full.csv"
OUT = ROOT / "anrw-submission" / "figures" / "fig_target_dist.pdf"

COLOR_BAR  = "#1f6feb"
COLOR_ZERO = "#d1495b"

vals = []
for chunk in pd.read_csv(CSV, usecols=["transfer_bytes"], chunksize=500_000):
    vals.append(chunk["transfer_bytes"].astype("float64").to_numpy())
tb = np.concatenate(vals)

n = len(tb)
n_zero = int((tb == 0).sum())
pct_zero = n_zero / n * 100
nonzero = tb[tb > 0]

print(f"Total rows: {n:,}")
print(f"Zeros:      {n_zero:,} ({pct_zero:.1f}%)")
print(f"Nonzero — mean {nonzero.mean():,.0f} B, median {np.median(nonzero):,.0f} B, max {nonzero.max():,.0f} B")

log_bins = np.logspace(0, np.log10(nonzero.max() * 1.05), 60)

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(5.5, 2.8))

ax.hist(nonzero, bins=log_bins, color=COLOR_BAR, edgecolor="white",
        linewidth=0.3, alpha=0.92)
ax.set_xscale("log")

# Annotate the zero spike off-axis (since log-x cannot show zero)
zero_count = n_zero
ax.axvline(0.5, color=COLOR_ZERO, linewidth=2, alpha=0.85)
ax.text(0.55, ax.get_ylim()[1] * 0.85,
        f"{pct_zero:.1f}%\nat $=0$\n(beacons)",
        fontsize=8, color=COLOR_ZERO, weight="bold", va="top")

# Mark the secondary mode
median_nz = np.median(nonzero)
mean_nz = nonzero.mean()
ax.axvline(median_nz, color="#444", linestyle=":", linewidth=1, alpha=0.7)
ax.text(median_nz, ax.get_ylim()[1] * 0.55, f"  median {median_nz:,.0f} B  ",
        fontsize=8, color="#444", va="center", rotation=90)

# Mark the heavy tail
tail_99 = np.quantile(nonzero, 0.99)
ax.axvline(tail_99, color="#444", linestyle=":", linewidth=1, alpha=0.7)
ax.text(tail_99, ax.get_ylim()[1] * 0.55, f"  p99 {tail_99/1024:,.0f} KB  ",
        fontsize=8, color="#444", va="center", rotation=90)

ax.set_xlabel("Transfer bytes  (log scale)")
ax.set_ylabel("Number of requests")
ax.set_xlim(0.4, nonzero.max() * 1.5)

# Format x ticks as bytes / KB / MB
def byte_fmt(x, _):
    if x < 1: return ""
    if x < 1024: return f"{int(x)} B"
    if x < 1024 ** 2: return f"{int(x / 1024)} KB"
    return f"{int(x / 1024 / 1024)} MB"

from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(byte_fmt))

# Clean spines
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color("#888")
ax.spines["bottom"].set_color("#888")
ax.tick_params(colors="#444", length=3)
ax.grid(axis="y", alpha=0.20, linestyle="-", linewidth=0.7)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
