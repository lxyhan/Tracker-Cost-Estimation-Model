"""
LUT-variants comparison: clean horizontal bar chart, sorted by MAE.

Figure 2 of the paper. Centerpiece for the "model beats every deployable LUT"
contribution. Each row is one estimator; bar length is held-out test MAE;
right annotation is artifact size at full-population scale; bar color
encodes deployability with the model highlighted.

Output: anrw-submission/figures/fig_lut_pareto.pdf
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "models" / "per_request" / "apr2026" / "lut_variants.json"
OUT = ROOT / "anrw-submission" / "figures" / "fig_lut_pareto.pdf"

# Consistent palette across all paper figures
COLOR_MODEL = "#1f6feb"     # strong blue
COLOR_DEPLOY = "#9aa6b4"    # neutral grey-blue
COLOR_NONDEPLOY = "#d1495b" # muted red

with open(INPUT) as f:
    variants = json.load(f)

LABEL_REWRITE = {
    "Domain only":                              "Domain",
    "Domain + type (deployed baseline)":         "Domain + Type  (deployed)",
    "Domain + type + has_query_params":         "  + has\\_query",
    "Domain + type + URL-length bucket (5)":    "  + URL-length bin",
    "Domain + type + first path token":         "  + first path token",
    "Domain + URL path (non-deployable)":       "Domain + URL path",
}

rows = [{"label": "Global median", "mae": 19905, "size_KB": 0, "category": "deployable"}]
for v in variants:
    rows.append({
        "label": LABEL_REWRITE.get(v["label"], v["label"]),
        "mae": v["mae"],
        "size_KB": v["size_KB_full_pop"],
        "category": "deployable" if v["deployable"] else "non-deployable",
    })
rows.append({"label": "Model (XGBoost+Tweedie)", "mae": 4246, "size_KB": 500,
             "category": "model"})

# Sort by MAE ascending so best at top
rows.sort(key=lambda r: r["mae"])

labels = [r["label"] for r in rows]
maes = [r["mae"] for r in rows]
colors = [COLOR_MODEL if r["category"] == "model"
          else (COLOR_NONDEPLOY if r["category"] == "non-deployable"
                else COLOR_DEPLOY)
          for r in rows]

def size_str(kb):
    if kb < 1: return "<1 KB"
    if kb < 1000: return f"{kb:.0f} KB"
    return f"{kb/1000:.0f} MB"

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(5.5, 3.0))
y = list(range(len(rows)))
ax.barh(y, maes, color=colors, edgecolor="white", linewidth=0.0, height=0.65)

ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.invert_yaxis()
ax.set_xlabel("Test-set MAE (bytes)")
ax.set_xlim(0, max(maes) * 1.50)

# Clean spines
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color("#888")
ax.spines["bottom"].set_color("#888")
ax.tick_params(colors="#444", length=3)
ax.grid(axis="x", alpha=0.20, linestyle="-", linewidth=0.7)
ax.set_axisbelow(True)

# Per-bar annotation: MAE | size | (✗ if non-deployable)
for yi, r in zip(y, rows):
    deploy_mark = " ✗" if r["category"] == "non-deployable" else ""
    text = f"  {int(round(r['mae'])):,} B  ·  {size_str(r['size_KB'])}{deploy_mark}"
    color = COLOR_NONDEPLOY if r["category"] == "non-deployable" else "#222"
    weight = "bold" if r["category"] == "model" else "normal"
    ax.text(r["mae"] + max(maes) * 0.015, yi, text, va="center",
            fontsize=9, color=color, weight=weight)

# Bold the model y-tick label, color-code others
for tick, r in zip(ax.get_yticklabels(), rows):
    if r["category"] == "model":
        tick.set_fontweight("bold")
        tick.set_color(COLOR_MODEL)

# Minimal legend
from matplotlib.patches import Patch
legend_elems = [
    Patch(facecolor=COLOR_MODEL, label="Model (this work)"),
    Patch(facecolor=COLOR_DEPLOY, label="Deployable LUT"),
    Patch(facecolor=COLOR_NONDEPLOY, label="Non-deployable (>5 MB)"),
]
ax.legend(handles=legend_elems, fontsize=8, loc="upper center", ncol=3,
          frameon=False, bbox_to_anchor=(0.5, -0.18),
          columnspacing=1.5, handletextpad=0.4)

plt.tight_layout()
plt.subplots_adjust(bottom=0.20)
plt.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {OUT}")
