"""
Cross-device validation: compare per-domain transfer-size statistics between
HTTP Archive's mobile crawl (training data) and desktop crawl (sql/11).

Tests whether the model's labels-invariance assumption holds across vantage
device. Complements the cross-browser UA-agreement test in §3.1(iii).

Run after both `data/raw/05_per_request_full/per_request_full.csv` and
`data/raw/11_desktop_jun2024/per_request_desktop_jun2024.csv` are populated.
"""

from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "data" / "raw" / "05_per_request_full" / "per_request_full.csv"
DESKTOP = ROOT / "data" / "raw" / "11_desktop_jun2024" / "per_request_desktop_jun2024.csv"
OUT = ROOT / "data" / "raw" / "cross_device_summary.csv"


def per_domain_stats(df: pd.DataFrame, label: str) -> pd.DataFrame:
    g = df.groupby("tracker_domain")["transfer_bytes"].agg(
        count="count", median="median", mean="mean").reset_index()
    g.columns = ["tracker_domain", f"{label}_count", f"{label}_median", f"{label}_mean"]
    return g


def main():
    print(f"Loading mobile data from {MOBILE}...")
    mobile = pd.read_csv(MOBILE, usecols=["tracker_domain", "transfer_bytes"], low_memory=False)
    mobile = mobile[mobile["transfer_bytes"].notna() & (mobile["transfer_bytes"] >= 0)]
    print(f"  {len(mobile):,} mobile rows, {mobile['tracker_domain'].nunique():,} domains")

    print(f"Loading desktop data from {DESKTOP}...")
    desktop = pd.read_csv(DESKTOP, usecols=["tracker_domain", "transfer_bytes"], low_memory=False)
    desktop = desktop[desktop["transfer_bytes"].notna() & (desktop["transfer_bytes"] >= 0)]
    print(f"  {len(desktop):,} desktop rows, {desktop['tracker_domain'].nunique():,} domains")

    m_stats = per_domain_stats(mobile, "mobile")
    d_stats = per_domain_stats(desktop, "desktop")

    joined = m_stats.merge(d_stats, on="tracker_domain", how="inner")
    print(f"\n  Domains in both: {len(joined):,}")

    # Filter to domains with reasonable sample size in both
    joined = joined[(joined["mobile_count"] >= 50) & (joined["desktop_count"] >= 50)]
    print(f"  Domains with >=50 reqs in both: {len(joined):,}")

    # Per-domain median ratios
    joined["median_ratio"] = (
        np.minimum(joined["mobile_median"], joined["desktop_median"]) /
        np.maximum(joined["mobile_median"], joined["desktop_median"]).clip(lower=1)
    )
    joined["mean_ratio"] = (
        np.minimum(joined["mobile_mean"], joined["desktop_mean"]) /
        np.maximum(joined["mobile_mean"], joined["desktop_mean"]).clip(lower=1)
    )

    joined.to_csv(OUT, index=False)

    print(f"\n=== Cross-device per-domain agreement ===")
    print(f"  N domains compared:                {len(joined):,}")
    print(f"  Median per-domain median ratio:    {joined['median_ratio'].median():.4f}")
    print(f"  Median per-domain mean ratio:      {joined['mean_ratio'].median():.4f}")
    print(f"  Fraction within 5% (median):       {(joined['median_ratio'] >= 0.95).mean()*100:.1f}%")
    print(f"  Fraction within 10% (median):      {(joined['median_ratio'] >= 0.90).mean()*100:.1f}%")
    print(f"  Fraction within 50% (median):      {(joined['median_ratio'] >= 0.50).mean()*100:.1f}%")
    print(f"  Fraction within 5% (mean):         {(joined['mean_ratio'] >= 0.95).mean()*100:.1f}%")
    print(f"  Fraction within 10% (mean):        {(joined['mean_ratio'] >= 0.90).mean()*100:.1f}%")
    print(f"\nWrote {OUT}")

    # Show worst disagreement examples
    worst = joined.nsmallest(10, "median_ratio")
    print(f"\n--- 10 worst per-domain median disagreements ---")
    for _, r in worst.iterrows():
        print(f"  {r['tracker_domain']:<35s}  mobile={r['mobile_median']:>10,.0f}  "
              f"desktop={r['desktop_median']:>10,.0f}  ratio={r['median_ratio']:.3f}")


if __name__ == "__main__":
    main()
