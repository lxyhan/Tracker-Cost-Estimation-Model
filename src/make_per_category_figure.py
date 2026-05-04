"""
Per-category byte concentration: visualizes Tab 1's headline finding.

Each Disconnect category is a row; two side-by-side horizontal bars show its
share of requests (light grey) vs.\ its share of bytes (blue). Categories
sorted by byte share descending.

The Tag-manager / Advertising inversion is the most quotable finding in the
paper; we highlight it by emphasizing those two rows' axis labels.

Output: anrw-submission/figures/fig_per_category.pdf
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "anrw-submission" / "figures" / "fig_per_category.pdf"

COLOR_REQ   = "#9aa6b4"
COLOR_BYTES = "#1f6feb"
COLOR_HI    = "#1f6feb"

rows = [
    ("Tag manager",     26,    6.3, 40.6),
    ("Content (CDN)",   573,   9.1, 25.3),
    ("Advertising",     2605, 66.5, 17.8),
    ("Social",          121,   7.9, 11.0),
    ("Analytics",       322,   8.6,  3.1),
    ("Other",           892,   0.8,  1.4),
    ("Consent provider", 38,   0.7,  0.8),
    ("Fingerprinting",   15,   0.1,  0.1),
]
rows.sort(key=lambda r: -r[3])

labels = [r[0] for r in rows]
ns     = [r[1] for r in rows]
reqs   = [r[2] for r in rows]
bytes_ = [r[3] for r in rows]

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(5.5, 2.6))

y = np.arange(len(labels))
h = 0.36
xmax = max(max(reqs), max(bytes_))

ax.barh(y - h/2, reqs,   height=h, color=COLOR_REQ,   edgecolor="white",
        linewidth=0.0, label="% of requests")
ax.barh(y + h/2, bytes_, height=h, color=COLOR_BYTES, edgecolor="white",
        linewidth=0.0, label="% of bytes")

ax.set_yticks(y)
ax.set_yticklabels([f"{lab}  ({n} dom.)" for lab, n in zip(labels, ns)])
ax.invert_yaxis()
ax.set_xlabel("Share of total tracker traffic (%)")
ax.set_xlim(0, xmax * 1.18)

for yi, (r_pct, b_pct) in enumerate(zip(reqs, bytes_)):
    ax.text(r_pct + xmax * 0.012, yi - h/2, f"{r_pct:.1f}",
            va="center", fontsize=8, color="#444")
    ax.text(b_pct + xmax * 0.012, yi + h/2, f"{b_pct:.1f}",
            va="center", fontsize=8, color="#222")

emphasized = {"Tag manager", "Advertising"}
for tick, (lab, *_) in zip(ax.get_yticklabels(), rows):
    if lab in emphasized:
        tick.set_color(COLOR_HI)
        tick.set_fontweight("bold")

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color("#888")
ax.spines["bottom"].set_color("#888")
ax.tick_params(colors="#444", length=3)
ax.grid(axis="x", alpha=0.20, linestyle="-", linewidth=0.7)
ax.set_axisbelow(True)

ax.legend(fontsize=8, loc="lower right", frameon=False)

plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
