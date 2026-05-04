"""
Claim B aggregation figure: model vs D+T LUT weekly aggregation %error
on the in-page Firefox crawl, at varying browsing scales N, for both
uniform and domain-correlated browsing simulations.

Output: anrw-submission/figures/fig_claim_b.pdf
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "anrw-submission" / "figures" / "fig_claim_b.pdf"

# Numbers from src/claim_b_aggregation.py output (current canonical model)
N = [50, 100, 200, 500]
model_uniform    = [26.8, 23.9, 23.4, 24.2]
lut_uniform      = [33.6, 31.4, 31.3, 31.5]
model_correlated = [42.1, 39.8, 38.2, 38.6]
lut_correlated   = [50.0, 48.6, 47.5, 47.6]

x = np.arange(len(N))
w = 0.20

fig, ax = plt.subplots(figsize=(5.5, 2.8))

# Bars
ax.bar(x - 1.5*w, model_uniform,    w, label="Model (uniform)",      color="C0", edgecolor="black", linewidth=0.5)
ax.bar(x - 0.5*w, lut_uniform,      w, label="D+T LUT (uniform)",    color="C0", edgecolor="black", linewidth=0.5, alpha=0.5, hatch="//")
ax.bar(x + 0.5*w, model_correlated, w, label="Model (correlated)",   color="C3", edgecolor="black", linewidth=0.5)
ax.bar(x + 1.5*w, lut_correlated,   w, label="D+T LUT (correlated)", color="C3", edgecolor="black", linewidth=0.5, alpha=0.5, hatch="//")

ax.set_xticks(x)
ax.set_xticklabels([f"N={n}" for n in N], fontsize=9)
ax.set_ylabel("Weekly aggregation error (%, median)", fontsize=10)
ax.set_xlabel("Browsing scale (tracker requests per week)", fontsize=10)
ax.set_ylim(0, 60)
ax.grid(axis="y", alpha=0.3)
# Place legend below the plot so it doesn't cover bars or axis labels
ax.legend(fontsize=8, loc="upper center", ncol=4, framealpha=0.95,
          bbox_to_anchor=(0.5, -0.22), columnspacing=0.8, handletextpad=0.4)

# Annotate the gap at N=200 for each scenario
for i, n in enumerate(N):
    if n != 200: continue
    gap_u = lut_uniform[i] - model_uniform[i]
    gap_c = lut_correlated[i] - model_correlated[i]
    # arrow between the model and LUT bars (uniform)
    ax.annotate(f"$+${gap_u:.1f}\\,pp", xy=(i - 1*w, max(model_uniform[i], lut_uniform[i]) + 1.5),
                fontsize=8, ha="center", color="C0", fontweight="bold")
    ax.annotate(f"$+${gap_c:.1f}\\,pp", xy=(i + 1*w, max(model_correlated[i], lut_correlated[i]) + 1.5),
                fontsize=8, ha="center", color="C3", fontweight="bold")

plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
