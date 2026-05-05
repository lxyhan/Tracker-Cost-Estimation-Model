"""
Claim B aggregation: model vs D+T LUT on the in-page Firefox crawl.

Uses the per-URL predictions in data/raw/claim_b_in_page_validation.csv,
adds per-request D+T LUT predictions from the saved domain encodings, and
runs the same weekly-aggregation simulation as the paper's Table 7
(uniform sampling and domain-correlated browsing).

The headline question: in deployment-realistic conditions (real Firefox,
mobile emulation, in-page browsing), how much better is the model than
the deployable LUT baseline at the user-facing weekly total?
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VAL_CSV = ROOT / "data" / "raw" / "claim_b_in_page_validation.csv"
ENC_PATH = ROOT / "models" / "per_request" / "apr2026" / "domain_encodings.json"


def add_lut_predictions(df: pd.DataFrame) -> pd.DataFrame:
    with open(ENC_PATH) as f:
        enc = json.load(f)
    domain_med = enc["domain_median"]
    dt_med = enc["domain_type_median"]
    global_med = enc["global_median"]

    def lookup(host: str, model_type: str) -> float:
        # First try domain+type; fall back to domain; then global
        # Also support suffix-walk for the domain (subdomains map up)
        parts = host.split(".")
        for i in range(len(parts) - 1):
            d = ".".join(parts[i:])
            dt = dt_med.get(f"{d}||{model_type}")
            if dt is not None:
                return dt
            dm = domain_med.get(d)
            if dm is not None:
                return dm
        return global_med

    df["lut_pred"] = [lookup(h, t) for h, t in zip(df["host"], df["model_type"])]
    return df


def aggregation_sim(df: pd.DataFrame, N_values=(50, 100, 200, 500),
                    n_trials=2000, seed=42, mode="uniform"):
    rng = np.random.default_rng(seed)
    results = []
    truths = df["transfer_bytes"].values
    model_preds = df["model_pred"].values
    lut_preds = df["lut_pred"].values
    domains = df["host"].values
    n = len(df)

    for N in N_values:
        model_pcts = np.empty(n_trials)
        lut_pcts = np.empty(n_trials)
        for t in range(n_trials):
            if mode == "uniform":
                idx = rng.integers(0, n, size=N)
            else:  # domain-correlated: pick 15 domains, sample from those
                unique_doms = np.unique(domains)
                pick_doms = rng.choice(unique_doms, size=min(15, len(unique_doms)),
                                       replace=False)
                mask = np.isin(domains, pick_doms)
                pool = np.where(mask)[0]
                if len(pool) == 0:
                    pool = np.arange(n)
                idx = rng.choice(pool, size=N, replace=True)
            true_sum = truths[idx].sum()
            if true_sum == 0:
                continue
            model_pcts[t] = abs(model_preds[idx].sum() - true_sum) / true_sum * 100
            lut_pcts[t]   = abs(lut_preds[idx].sum()   - true_sum) / true_sum * 100
        results.append({
            "N": N,
            "model_median_pct": float(np.median(model_pcts)),
            "lut_median_pct":   float(np.median(lut_pcts)),
            "model_p90_pct":    float(np.percentile(model_pcts, 90)),
            "lut_p90_pct":      float(np.percentile(lut_pcts, 90)),
            "model_within_10pct": float((model_pcts <= 10).mean()),
            "lut_within_10pct":   float((lut_pcts <= 10).mean()),
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-csv", default=str(VAL_CSV),
                    help="Per-request validation CSV from claim_b_har_analysis.py "
                         "(default: data/raw/claim_b_in_page_validation.csv).")
    args = ap.parse_args()
    val_csv = Path(args.val_csv)

    df = pd.read_csv(val_csv)
    print(f"Loaded {len(df):,} in-page tracker requests from {val_csv}")
    df = add_lut_predictions(df)
    print(f"Added LUT predictions (D+T fallback chain)")
    print()
    print(f"Per-request error summary:")
    df["model_abs_err"] = (df["model_pred"] - df["transfer_bytes"]).abs()
    df["lut_abs_err"]   = (df["lut_pred"]   - df["transfer_bytes"]).abs()
    print(f"  Model MAE:  {df['model_abs_err'].mean():>10,.0f} B  median: {df['model_abs_err'].median():>8,.0f}")
    print(f"  LUT MAE:    {df['lut_abs_err'].mean():>10,.0f} B  median: {df['lut_abs_err'].median():>8,.0f}")

    print(f"\n=== UNIFORM SAMPLING (median % error) ===")
    print(f"  {'N':>4s}  {'Model':>8s}  {'LUT':>8s}  {'Mod p90':>8s}  {'LUT p90':>8s}  {'Mod w/in 10%':>12s}  {'LUT w/in 10%':>12s}")
    for r in aggregation_sim(df, mode="uniform"):
        print(f"  {r['N']:>4d}  {r['model_median_pct']:>7.1f}%  {r['lut_median_pct']:>7.1f}%  "
              f"{r['model_p90_pct']:>7.1f}%  {r['lut_p90_pct']:>7.1f}%  "
              f"{r['model_within_10pct']*100:>11.1f}%  {r['lut_within_10pct']*100:>11.1f}%")

    print(f"\n=== DOMAIN-CORRELATED (15 domains per trial; median % error) ===")
    print(f"  {'N':>4s}  {'Model':>8s}  {'LUT':>8s}  {'Mod p90':>8s}  {'LUT p90':>8s}  {'Mod w/in 10%':>12s}  {'LUT w/in 10%':>12s}")
    for r in aggregation_sim(df, mode="correlated"):
        print(f"  {r['N']:>4d}  {r['model_median_pct']:>7.1f}%  {r['lut_median_pct']:>7.1f}%  "
              f"{r['model_p90_pct']:>7.1f}%  {r['lut_p90_pct']:>7.1f}%  "
              f"{r['model_within_10pct']*100:>11.1f}%  {r['lut_within_10pct']*100:>11.1f}%")


if __name__ == "__main__":
    main()
