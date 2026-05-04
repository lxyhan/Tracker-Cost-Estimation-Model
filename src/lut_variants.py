"""
Evaluate intermediate-granularity LUT variants to defend against the
strawman objection: D+T LUT isn't the only non-model option.

Variants (in order of increasing granularity):
  1. Global median (1 entry)
  2. Domain (~6K entries)
  3. Domain + resource_type (~30K entries)         ← deployable baseline
  4. Domain + type + URL-length bucket (~150K entries)
  5. Domain + type + has_query_params (~60K entries)
  6. Domain + type + first path token (~500K entries)
  7. Domain + URL path (~23M entries)              ← non-deployable upper bound

For each: report MAE on April 2026 test split + estimated storage size at
full population scale.

Run after train_multi_target.py has produced canonical artifacts.
"""

from __future__ import annotations
import json, re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "17_recent_apr2026" / "per_request_apr2026.csv"
MODELS = ROOT / "models" / "per_request"
OUT = MODELS / "lut_variants.json"

# Storage estimate per entry: 8-byte key hash + 4-byte median value (compact binary).
# Domain string + JSON wouldn't fit in 12B but a deployed LUT would use compact form.
BYTES_PER_ENTRY = 12

# Scaling factor for entry counts from 1% sample to full population.
# CRITICAL: this is NOT 100x for domain-keyed LUTs because the unique-domain
# set is bounded (HTTP Archive tracks ~5-10K third-party domains total).
# Path-keyed LUTs DO scale ~linearly because each URL path is unique. We
# pass a per-LUT factor below.


def url_length_bucket(L: int) -> str:
    if L < 50: return "xs"
    if L < 100: return "s"
    if L < 200: return "m"
    if L < 400: return "l"
    return "xl"


def first_token(p: str) -> str:
    if not isinstance(p, str): return ""
    parts = re.split(r"[/?&=._-]+", p.lstrip("/"))
    return parts[0] if parts else ""


def evaluate_lut(train_df, test_df, key_cols, label, scale_to_full):
    """Compute median per key on train, score on test, return MAE + size.

    scale_to_full: factor to extrapolate entry count from 1% sample to full
    population. Domain-keyed LUTs are nearly saturated (factor ~1.2);
    path-keyed LUTs scale linearly (factor ~100)."""
    medians = train_df.groupby(key_cols)["transfer_bytes"].median().to_dict()
    domain_medians = train_df.groupby("tracker_domain")["transfer_bytes"].median().to_dict()
    global_med = train_df["transfer_bytes"].median()

    def predict(row):
        key = tuple(row[c] for c in key_cols) if len(key_cols) > 1 else row[key_cols[0]]
        if key in medians: return medians[key]
        d = row["tracker_domain"]
        if d in domain_medians: return domain_medians[d]
        return global_med

    preds = test_df.apply(predict, axis=1).values
    mae = mean_absolute_error(test_df["transfer_bytes"].values, preds)
    n_entries = len(medians)
    n_full = int(n_entries * scale_to_full)
    size_bytes_full = n_full * BYTES_PER_ENTRY
    return {
        "label": label,
        "key": "+".join(key_cols),
        "mae": float(mae),
        "n_entries_sample": int(n_entries),
        "n_entries_full_pop": n_full,
        "size_KB_full_pop": int(size_bytes_full / 1024),
        "deployable": size_bytes_full < 5e6,  # 5MB threshold (EasyList ~5MB)
    }


def main():
    print(f"Loading {DATA}...")
    df = pd.read_csv(DATA, low_memory=False)
    df = df[df["transfer_bytes"].notna() & (df["transfer_bytes"] >= 0)].copy()
    print(f"  {len(df):,} rows")

    # Same split as training (seed 42, 70/15/15)
    np.random.seed(42)
    n = len(df)
    idx = np.random.permutation(n)
    train_df = df.iloc[idx[: int(0.7 * n)]].reset_index(drop=True)
    test_df = df.iloc[idx[int(0.85 * n):]].reset_index(drop=True)
    print(f"  train: {len(train_df):,}, test: {len(test_df):,}")

    # Build feature columns for variants
    test_df["url_length_bucket"] = test_df["url_length"].fillna(0).astype(int).apply(url_length_bucket)
    train_df["url_length_bucket"] = train_df["url_length"].fillna(0).astype(int).apply(url_length_bucket)
    test_df["first_path_token"] = test_df["url_path"].apply(first_token)
    train_df["first_path_token"] = train_df["url_path"].apply(first_token)

    # (key_cols, label, scale_factor)
    # Domain-keyed: ~1.2x (set is bounded by tracker ecosystem ~5-10K)
    # Token-keyed: ~5x (some path-prefix variability not captured in 1%)
    # Path-keyed: ~100x (each URL is unique, scales linearly)
    variants = [
        (["tracker_domain"],                                      "Domain only",                            1.2),
        (["tracker_domain", "resource_type"],                      "Domain + type (deployed baseline)",      1.2),
        (["tracker_domain", "resource_type", "has_query_params"], "Domain + type + has_query_params",       1.2),
        (["tracker_domain", "resource_type", "url_length_bucket"], "Domain + type + URL-length bucket (5)",  1.5),
        (["tracker_domain", "resource_type", "first_path_token"], "Domain + type + first path token",       3.0),
        (["tracker_domain", "url_path"],                           "Domain + URL path (non-deployable)",    100.0),
    ]

    results = []
    print(f"\n{'Label':<46s}  {'MAE':>8s}  {'Entries (1%)':>14s}  {'Entries (full)':>15s}  {'Size@full':>10s}  {'Deploy?':>8s}")
    print("-" * 115)
    for keys, label, scale in variants:
        r = evaluate_lut(train_df, test_df, keys, label, scale)
        results.append(r)
        print(f"{label:<46s}  {r['mae']:>8,.0f}  {r['n_entries_sample']:>14,d}  "
              f"{r['n_entries_full_pop']:>15,d}  {r['size_KB_full_pop']:>9,d}KB  "
              f"{('YES' if r['deployable'] else 'NO'):>8s}")

    # Add headline model + global for context
    print()
    print(f"  (For reference: April 2026 model MAE = ~4,300 at 500KB ONNX; global median MAE = ~13,600 at <1KB)")

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
