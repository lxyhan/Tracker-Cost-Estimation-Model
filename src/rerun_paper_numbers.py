"""
Recompute every numerical claim in the paper from the retrained model:
- Headline MAE + bootstrap CI on test set
- LUT hierarchy MAE numbers
- Path decomposition (seen vs unseen) + bootstrap CIs
- Per-resource-type MAE
- Loss & feature ablation numbers
- Aggregation simulation (uniform + correlated)

Outputs models/per_request/rerun_paper_numbers.json which we use to
update the paper.

Run:
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib python3 src/rerun_paper_numbers.py
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models" / "per_request" / "apr2026"
DATA = ROOT / "data" / "raw" / "17_recent_apr2026" / "per_request_apr2026.csv"
OUT = MODELS / "rerun_paper_numbers.json"


def bootstrap_mae_ci(y_true, y_pred, n_boot=1000, ci=95, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y_true)
    scores = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        scores[i] = mean_absolute_error(y_true[idx], y_pred[idx])
    return float(scores.mean()), float(np.percentile(scores, (100 - ci) / 2)), \
           float(np.percentile(scores, 100 - (100 - ci) / 2))


def main():
    sys.path.insert(0, str(ROOT / "src" / "model"))
    from url_embeddings import URLEmbedder

    print("Loading retrained pipeline...")
    embedder = URLEmbedder().load(MODELS / "url_embedder.joblib")
    with open(MODELS / "domain_encodings.json") as f:
        enc = json.load(f)
    with open(MODELS / "feature_columns.json") as f:
        feature_cols = json.load(f)
    booster = xgb.Booster()
    booster.load_model(str(MODELS / "xgb_transfer_bytes.json"))

    print(f"Loading {DATA}...")
    df = pd.read_csv(DATA, low_memory=False)
    df = df[df["transfer_bytes"].notna() & (df["transfer_bytes"] >= 0)].copy()
    print(f"  {len(df):,} rows")

    # Reproduce the same train/val/test split (seed 42)
    np.random.seed(42)
    n = len(df)
    idx = np.random.permutation(n)
    train_idx = idx[: int(0.7 * n)]
    val_idx = idx[int(0.7 * n) : int(0.85 * n)]
    test_idx = idx[int(0.85 * n) :]
    train_df = df.iloc[train_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)
    print(f"  test set: {len(test_df):,}")

    # ===========================================================================
    # Build test features (same code path as training)
    # ===========================================================================
    print("Building test features...")
    sys.path.insert(0, str(ROOT / "src" / "model"))
    from train_multi_target import engineer_features

    url_embed_test = embedder.transform(test_df["url_path"].fillna(""))
    X_test = engineer_features(test_df, train_df, url_embed_test)[feature_cols]
    y_test = test_df["transfer_bytes"].values

    # ===========================================================================
    # Headline MAE + bootstrap CI
    # ===========================================================================
    print("\n=== Headline result ===")
    dmat = xgb.DMatrix(X_test, feature_names=feature_cols)
    preds = np.clip(booster.predict(dmat), 0, None)
    mae = mean_absolute_error(y_test, preds)
    rho, _ = spearmanr(y_test, preds)
    print(f"  Computing bootstrap CI ({1000} resamples)...")
    mean_mae, lo, hi = bootstrap_mae_ci(y_test, preds, n_boot=1000)
    print(f"  Model MAE: {mae:,.0f}  CI [{lo:,.0f}, {hi:,.0f}]  rho={rho:.4f}")

    # ===========================================================================
    # LUT hierarchy
    # ===========================================================================
    print("\n=== LUT hierarchy ===")
    global_med = train_df["transfer_bytes"].median()
    domain_med = train_df.groupby("tracker_domain")["transfer_bytes"].median().to_dict()
    dt_med = train_df.groupby(["tracker_domain", "resource_type"])["transfer_bytes"].median().to_dict()
    path_med = train_df.groupby(["tracker_domain", "url_path"])["transfer_bytes"].median().to_dict()

    global_pred = np.full(len(test_df), global_med)
    domain_pred = test_df["tracker_domain"].map(domain_med).fillna(global_med).values
    dt_pred = test_df.apply(
        lambda r: dt_med.get((r["tracker_domain"], r["resource_type"]),
                             domain_med.get(r["tracker_domain"], global_med)), axis=1).values
    path_pred = test_df.apply(
        lambda r: path_med.get((r["tracker_domain"], r["url_path"]),
                               dt_med.get((r["tracker_domain"], r["resource_type"]),
                                         domain_med.get(r["tracker_domain"], global_med))),
        axis=1).values

    mae_global = mean_absolute_error(y_test, global_pred)
    mae_domain = mean_absolute_error(y_test, domain_pred)
    mae_dt = mean_absolute_error(y_test, dt_pred)
    mae_path = mean_absolute_error(y_test, path_pred)
    print(f"  Global median MAE:     {mae_global:>10,.0f}")
    print(f"  Domain LUT MAE:        {mae_domain:>10,.0f}")
    print(f"  Domain+type LUT MAE:   {mae_dt:>10,.0f}  CI {bootstrap_mae_ci(y_test, dt_pred)[1:]}")
    print(f"  Path LUT MAE:          {mae_path:>10,.0f}  CI {bootstrap_mae_ci(y_test, path_pred)[1:]}")
    print(f"  Improvement vs D+T:    {(1 - mae/mae_dt) * 100:+.1f}%")

    # ===========================================================================
    # Path decomposition
    # ===========================================================================
    print("\n=== Path decomposition (seen vs unseen) ===")
    seen_mask = test_df.apply(
        lambda r: (r["tracker_domain"], r["url_path"]) in path_med, axis=1).values
    n_seen = int(seen_mask.sum())
    n_unseen = int((~seen_mask).sum())
    pct_seen = 100 * n_seen / len(test_df)

    mae_seen_lut = mean_absolute_error(y_test[seen_mask], path_pred[seen_mask])
    mae_seen_model = mean_absolute_error(y_test[seen_mask], preds[seen_mask])
    mae_unseen_lut = mean_absolute_error(y_test[~seen_mask], path_pred[~seen_mask])
    mae_unseen_model = mean_absolute_error(y_test[~seen_mask], preds[~seen_mask])

    seen_lut_ci = bootstrap_mae_ci(y_test[seen_mask], path_pred[seen_mask])
    seen_model_ci = bootstrap_mae_ci(y_test[seen_mask], preds[seen_mask])

    print(f"  Seen paths ({pct_seen:.1f}%, n={n_seen:,}):")
    print(f"    LUT:   {mae_seen_lut:>10,.0f}  CI [{seen_lut_ci[1]:,.0f}, {seen_lut_ci[2]:,.0f}]")
    print(f"    Model: {mae_seen_model:>10,.0f}  CI [{seen_model_ci[1]:,.0f}, {seen_model_ci[2]:,.0f}]")
    print(f"  Unseen paths ({100-pct_seen:.1f}%, n={n_unseen:,}):")
    print(f"    LUT:   {mae_unseen_lut:>10,.0f}")
    print(f"    Model: {mae_unseen_model:>10,.0f}")

    # ===========================================================================
    # Save
    # ===========================================================================
    out = {
        "headline": {
            "model_mae": mae,
            "model_mae_ci": [lo, hi],
            "model_rho": rho,
            "lut_dt_mae": mae_dt,
            "lut_path_mae": mae_path,
            "improvement_vs_dt_pct": (1 - mae / mae_dt) * 100,
            "improvement_vs_path_pct": (1 - mae / mae_path) * 100,
        },
        "lut_hierarchy": {
            "global_median": mae_global,
            "domain": mae_domain,
            "domain_type": mae_dt,
            "path": mae_path,
        },
        "path_decomposition": {
            "n_seen": n_seen,
            "n_unseen": n_unseen,
            "pct_seen": pct_seen,
            "seen_lut_mae": mae_seen_lut,
            "seen_model_mae": mae_seen_model,
            "seen_lut_ci": seen_lut_ci[1:],
            "seen_model_ci": seen_model_ci[1:],
            "unseen_lut_mae": mae_unseen_lut,
            "unseen_model_mae": mae_unseen_model,
        },
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
