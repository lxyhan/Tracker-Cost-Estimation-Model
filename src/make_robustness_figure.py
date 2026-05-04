"""
Combined robustness figure: temporal degradation + in-page Firefox aggregation.

Both panels show the same metric — weekly aggregation % error — across two
different stress axes: time (left) and browsing scale (right). Tells the
"model maintains advantage as conditions vary" story in one figure.

Output: anrw-submission/figures/fig_robustness.pdf
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "anrw-submission" / "figures" / "fig_robustness.pdf"

# Consistent palette across paper figures
COLOR_MODEL = "#1f6feb"
COLOR_LUT   = "#9aa6b4"
COLOR_FILL  = "#1f6feb"

# --- Panel A: temporal aggregation error ---
horizons_x = [0, 1, 3, 6]
horizons_label = ["In-dist.", "1\mo", "3\mo", "6\mo"]
model_agg = [6.0, 8.0, 10.7, 13.9]
lut_agg   = [21.9, 21.3, 21.5, 19.6]

# --- Panel B: Claim B aggregation (in-page Firefox) ---
N = [50, 100, 200, 500]
model_uniform    = [26.8, 23.9, 23.4, 24.2]
lut_uniform      = [33.6, 31.4, 31.3, 31.5]
model_correlated = [42.1, 39.8, 38.2, 38.6]
lut_correlated   = [50.0, 48.6, 47.5, 47.6]

plt.rcParams["font.size"] = 10
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.7))

# === Panel A ===
ax1.plot(horizons_x, lut_agg,   "o-", color=COLOR_LUT,   linewidth=2,
         markersize=7, label="D+T LUT")
ax1.plot(horizons_x, model_agg, "o-", color=COLOR_MODEL, linewidth=2,
         markersize=7, label="Model")
ax1.fill_between(horizons_x, model_agg, lut_agg, color=COLOR_FILL, alpha=0.10)

ax1.set_xticks(horizons_x)
ax1.set_xticklabels(horizons_label)
ax1.set_ylabel("Weekly aggregation % error  (N=200)")
ax1.set_xlabel("Staleness horizon")
ax1.set_title("(a) Temporal robustness", fontsize=10, pad=8)
ax1.set_ylim(0, 28)

# Annotate the shrinking gap
ax1.annotate(f"{lut_agg[0] - model_agg[0]:.1f} pp", xy=(0, (lut_agg[0]+model_agg[0])/2),
             xytext=(0.3, 13), fontsize=8, color=COLOR_MODEL)
ax1.annotate(f"{lut_agg[3] - model_agg[3]:.1f} pp", xy=(6, (lut_agg[3]+model_agg[3])/2),
             xytext=(5.4, 16.5), fontsize=8, color=COLOR_MODEL)

# === Panel B ===
x = np.arange(len(N))
ax2.plot(x, lut_uniform,      "o-",  color=COLOR_LUT,   linewidth=2, markersize=7,
         label="D+T LUT (uniform)")
ax2.plot(x, model_uniform,    "o-",  color=COLOR_MODEL, linewidth=2, markersize=7,
         label="Model (uniform)")
ax2.plot(x, lut_correlated,   "o--", color=COLOR_LUT,   linewidth=2, markersize=7,
         label="D+T LUT (correlated)")
ax2.plot(x, model_correlated, "o--", color=COLOR_MODEL, linewidth=2, markersize=7,
         label="Model (correlated)")

ax2.set_xticks(x)
ax2.set_xticklabels([f"N={n}" for n in N])
ax2.set_xlabel("Browsing scale (tracker reqs / week)")
ax2.set_title("(b) In-page Firefox deployment", fontsize=10, pad=8)
ax2.set_ylim(0, 60)

# Clean both axes
for ax in (ax1, ax2):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#888")
    ax.spines["bottom"].set_color("#888")
    ax.tick_params(colors="#444", length=3)
    ax.grid(axis="y", alpha=0.20, linestyle="-", linewidth=0.7)
    ax.set_axisbelow(True)

# Single shared legend below both panels
from matplotlib.lines import Line2D
shared_legend = [
    Line2D([0], [0], marker="o", linestyle="-",  color=COLOR_MODEL, label="Model (uniform / temporal)"),
    Line2D([0], [0], marker="o", linestyle="-",  color=COLOR_LUT,   label="D+T LUT (uniform / temporal)"),
    Line2D([0], [0], marker="o", linestyle="--", color=COLOR_MODEL, label="Model (correlated)"),
    Line2D([0], [0], marker="o", linestyle="--", color=COLOR_LUT,   label="D+T LUT (correlated)"),
]
fig.legend(handles=shared_legend, loc="lower center", ncol=4, fontsize=8,
           frameon=False, bbox_to_anchor=(0.5, -0.02), columnspacing=1.2,
           handletextpad=0.4, handlelength=2.0)

plt.tight_layout()
plt.subplots_adjust(bottom=0.22)
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
