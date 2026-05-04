"""
Generate a 2-panel figure: temporal degradation curve.
- Left panel: per-request MAE for Model vs D+T LUT across in-dist + 1/3/6 month horizons
- Right panel: weekly aggregation % error for Model vs D+T LUT across same horizons

Output: figures/fig_temporal_curve.pdf
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "anrw-submission" / "figures" / "fig_temporal_curve.pdf"

# In-distribution + 1/3/6 month numbers (from rerun_paper_numbers.json + temporal_curve.json)
horizons_label = ["In-dist\n(June)", "1 mo\n(July)", "3 mo\n(Sept)", "6 mo\n(Dec)"]
horizons_x = [0, 1, 3, 6]

# Per-request MAE
model_mae = [3705, 4454, 4776, 5256]   # June 2024 model evaluated at each horizon
lut_mae   = [6578, 6694, 6721, 7069]

# Aggregation % error (median, N=200 uniform)
model_agg = [6.0, 8.0, 10.7, 13.9]
lut_agg   = [21.9, 21.3, 21.5, 19.6]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.5))

# Left: per-request MAE
ax1.plot(horizons_x, model_mae, "o-", color="C0", linewidth=2,
         markersize=6, label="Model")
ax1.plot(horizons_x, lut_mae,   "s--", color="C3", linewidth=2,
         markersize=6, label="D+T LUT")
ax1.set_xticks(horizons_x)
ax1.set_xticklabels(horizons_label, fontsize=9)
ax1.set_ylabel("Per-request MAE (B)", fontsize=10)
ax1.set_xlabel("Staleness horizon", fontsize=10)
ax1.set_title("(a) Per-request accuracy", fontsize=10)
ax1.grid(alpha=0.3)
ax1.legend(fontsize=9, loc="lower right")
ax1.set_ylim(bottom=0)

# Right: aggregation % error (N=200)
ax2.plot(horizons_x, model_agg, "o-", color="C0", linewidth=2,
         markersize=6, label="Model")
ax2.plot(horizons_x, lut_agg,   "s--", color="C3", linewidth=2,
         markersize=6, label="D+T LUT")
ax2.set_xticks(horizons_x)
ax2.set_xticklabels(horizons_label, fontsize=9)
ax2.set_ylabel("Weekly agg. error (%, $N{=}200$)", fontsize=10)
ax2.set_xlabel("Staleness horizon", fontsize=10)
ax2.set_title("(b) User-facing aggregation", fontsize=10)
ax2.grid(alpha=0.3)
ax2.legend(fontsize=9, loc="lower right")
ax2.set_ylim(0, 28)

plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
