"""
Claim B: deployment-side validation of the trained model.

For each tracker URL we fetched in `data/raw/ua_agreement.csv`, run the
model's prediction and compare to the actual Firefox-fetched bytes.

This is a small empirical version of the telemetry-replay future work
described in §6: model says "X bytes"; the live fetch says "Y bytes";
we measure the gap.

Prerequisite: train_multi_target.py must have run successfully and saved:
- models/per_request/url_embedder.joblib
- models/per_request/domain_encodings.json
- models/per_request/feature_columns.json
- models/per_request/xgb_transfer_bytes.json

Run:
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib python3 src/claim_b_validation.py
"""

from __future__ import annotations
import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UA_CSV = ROOT / "data" / "raw" / "ua_agreement.csv"
OUT = ROOT / "data" / "raw" / "ua_validation.csv"


def infer_resource_type(url: str) -> str:
    """Heuristic: guess Firefox resource_type from URL extension."""
    path_lower = urlparse(url).path.lower()
    if path_lower.endswith(".js") or "sdk" in path_lower or "tag" in path_lower:
        return "script"
    if any(path_lower.endswith(ext) for ext in (".png", ".gif", ".jpg", ".jpeg")):
        return "image"
    if path_lower.endswith(".css"):
        return "css"
    if path_lower.endswith(".html"):
        return "html"
    if "collect" in path_lower or "beacon" in path_lower or "pixel" in path_lower:
        return "other"
    return "script"  # default — most tracker URLs are scripts


def main():
    sys.path.insert(0, str(ROOT / "src" / "model"))
    from inference_pipeline import InferencePipeline

    print("Loading inference pipeline...")
    pipe = InferencePipeline()
    print(f"  feature_cols: {len(pipe.feature_cols)}")
    print(f"  domains in encoding table: {len(pipe.encodings['domain_median']):,}")
    print(f"  global median fallback: {pipe.global_median:.0f}")

    rows = []
    with open(UA_CSV) as f:
        for r in csv.DictReader(f):
            if r["ff_status"] == "200" and r["ch_status"] == "200":
                rows.append(r)
    print(f"\nValidating on {len(rows)} URL pairs...")

    results = []
    for r in rows:
        url = r["url"]
        ff_bytes = int(r["ff_bytes"])
        ch_bytes = int(r["ch_bytes"])
        rt = infer_resource_type(url)
        try:
            pred = pipe.predict(url, resource_type=rt)
        except Exception as e:
            print(f"  predict failed for {url[:60]}: {e}")
            continue
        results.append({
            "url": url, "resource_type": rt,
            "ff_bytes": ff_bytes, "ch_bytes": ch_bytes,
            "model_pred": pred,
            "abs_err_ff": abs(pred - ff_bytes),
            "abs_err_ch": abs(pred - ch_bytes),
        })

    if not results:
        print("No successful predictions; aborting.")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    ff_errs = np.array([r["abs_err_ff"] for r in results])
    ch_errs = np.array([r["abs_err_ch"] for r in results])
    ff_byt = np.array([r["ff_bytes"] for r in results])
    preds = np.array([r["model_pred"] for r in results])

    mae_ff = ff_errs.mean()
    medae_ff = np.median(ff_errs)
    mae_ch = ch_errs.mean()
    spear = np.corrcoef(np.argsort(np.argsort(ff_byt)),
                        np.argsort(np.argsort(preds)))[0, 1]
    within_50pct = np.mean(np.abs(preds - ff_byt) <= 0.5 * np.maximum(ff_byt, 1))
    within_2x = np.mean(
        np.maximum(preds, ff_byt) <= 2 * np.maximum(np.minimum(preds, ff_byt), 1)
    )

    print(f"\n=== Claim B: model predictions vs Firefox-fetched bytes ===")
    print(f"  N URLs:                          {len(results)}")
    print(f"  MAE vs Firefox bytes:            {mae_ff:>10,.0f} B")
    print(f"  Median absolute error vs FF:     {medae_ff:>10,.0f} B")
    print(f"  MAE vs Chrome bytes (sanity):    {mae_ch:>10,.0f} B")
    print(f"  Spearman rho (pred vs ff_bytes): {spear:>10.4f}")
    print(f"  Fraction within 50% of truth:    {within_50pct*100:.1f}%")
    print(f"  Fraction within 2x of truth:     {within_2x*100:.1f}%")
    print(f"\nWrote {OUT}")

    # Show a few examples
    print(f"\n--- 10 representative predictions ---")
    sorted_results = sorted(results, key=lambda r: r["ff_bytes"])
    for r in sorted_results[::max(1, len(sorted_results)//10)][:10]:
        print(f"  ff={r['ff_bytes']:>8,}  pred={r['model_pred']:>8,.0f}  "
              f"err={abs(r['model_pred']-r['ff_bytes']):>8,.0f}  {r['url'][:60]}")


if __name__ == "__main__":
    main()
