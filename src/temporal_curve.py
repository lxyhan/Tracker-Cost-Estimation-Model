"""
Multi-horizon temporal evaluation: train on June, evaluate on July, September,
December, and the following June.

Produces a degradation curve directly addressing the supervisor-flagged
"longer horizons unmeasured" limitation.

Run:
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib python3 src/temporal_curve.py
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
# Temporal study uses the JUNE 2024 model deliberately (backed up at jun2024/)
# rather than the canonical April 2026 model. This is the apples-to-apples
# evaluation: train on June 2024, test at 1/3/6/12 month horizons.
MODELS = ROOT / "models" / "per_request" / "jun2024"
RAW = ROOT / "data" / "raw"

HORIZONS = [
    ("July 2024",      "08_temporal_jul2024",      "per_request_1pct_jul2024.csv",      1),
    ("September 2024", "07_temporal_sep2024",      "per_request_1pct_sep2024.csv",      3),
    ("December 2024",  "09_temporal_dec2024",      "per_request_1pct_dec2024.csv",      6),
    ("June 2025",      "10_temporal_jun2025",      "per_request_1pct_jun2025.csv",     12),
]


def load_pipeline():
    sys.path.insert(0, str(ROOT / "src" / "model"))
    from inference_pipeline import InferencePipeline
    return InferencePipeline()


def build_features_full(df: pd.DataFrame, encodings: dict, url_embed,
                        feature_cols: list, six_type_model: bool = True):
    """Build the FULL feature matrix matching the trained model. Mirrors
    `inference_pipeline._engineer` but vectorized for batch scoring."""
    import re
    domain_med = pd.Series(encodings["domain_median"])
    dt_med = encodings["domain_type_median"]
    global_med = encodings["global_median"]
    domain_vol = encodings.get("domain_volume", {})

    feats = pd.DataFrame(index=df.index)
    # Target encodings
    feats["domain_median_bytes"] = df["tracker_domain"].map(domain_med).fillna(global_med).values
    feats["domain_type_median"] = [
        dt_med.get(f"{d}||{rt}", domain_med.get(d, global_med))
        for d, rt in zip(df["tracker_domain"], df["resource_type"])
    ]
    feats["domain_volume"] = np.log1p(df["tracker_domain"].map(lambda d: domain_vol.get(d, 0)).fillna(0))

    # Numeric / boolean URL structure
    feats["path_depth"] = df["path_depth"].fillna(0)
    feats["url_length"] = df["url_length"].fillna(0)
    feats["num_query_params"] = df["num_query_params"].fillna(0)
    feats["has_query_params"] = df["has_query_params"].astype(int)
    feats["path_token_count"] = df["url_path"].fillna("").str.count("/")
    feats["waterfall_index"] = df.get("waterfall_index", 0).fillna(0) if "waterfall_index" in df else 0
    feats["is_https"] = df.get("is_https", 1).fillna(1) if "is_https" in df else 1

    # Resource type one-hots (6 or 11 depending on model)
    rt_list = (["script", "image", "other", "html", "text", "css"] if six_type_model
               else ["script", "image", "other", "html", "text", "json", "css", "font", "video", "xml", "audio"])
    for rt in rt_list:
        feats[f"rt_{rt}"] = (df["resource_type"] == rt).astype(int)

    # Initiator type
    for it in ["script", "parser", "other", "preflight"]:
        feats[f"init_{it}"] = (df["initiator_type"] == it).astype(int)

    # HTTP method
    for m in ["GET", "POST"]:
        feats[f"method_{m}"] = (df["http_method"] == m).astype(int)
    feats["is_post"] = (df["http_method"] == "POST").astype(int)

    # HTTP version
    for v in ["HTTP/2", "h3", "http/1.1"]:
        col = f"httpv_{v}"
        feats[col] = (df["http_version"] == v).astype(int)

    # File extension
    EXT_GROUPS = {"js", "gif", "html", "php", "jpg", "json", "png", "css"}
    ext_clean = df["file_extension"].apply(lambda x: x if x in EXT_GROUPS else ("other" if pd.notna(x) else "none"))
    for e in list(EXT_GROUPS) + ["other", "none"]:
        feats[f"ext_{e}"] = (ext_clean == e).astype(int)

    # Priority ordinal
    PRIORITY_MAP = {"Lowest": 0, "Low": 1, "Medium": 2, "High": 3, "Highest": 4}
    feats["priority_ord"] = df["chrome_priority"].map(PRIORITY_MAP).fillna(1)

    # URL content regex flags
    URL_PATTERNS = {
        "path_has_js": r"\.js|/js/|script|sdk|lib|tag|gtm|gtag",
        "path_has_collect": r"collect|beacon|ping|pixel|track",
        "path_has_image": r"\.gif|\.png|\.jpg|pixel|1x1",
        "path_has_sync": r"sync|match|cookie|usersync",
        "path_has_ad": r"/ad/|/ads/|adserver|pagead|prebid",
        "path_has_api": r"/api/|/v[0-9]/|/collect|/event",
    }
    path = df["url_path"].fillna("")
    for name, pattern in URL_PATTERNS.items():
        feats[name] = path.str.contains(pattern, case=False, regex=True).astype(int)

    # URL embedding
    for i in range(url_embed.shape[1]):
        feats[f"url_emb_{i}"] = url_embed[:, i]

    # Fill missing columns with 0 then select training column order
    for col in feature_cols:
        if col not in feats.columns:
            feats[col] = 0.0
    return feats[feature_cols]


def evaluate_csv(csv_path: Path, model_dir: Path, six_type_model: bool = True):
    """Score one holdout CSV with the full feature set."""
    df = pd.read_csv(csv_path, low_memory=False)
    df = df[df["transfer_bytes"].notna() & (df["transfer_bytes"] >= 0)].copy()
    print(f"  Loaded {len(df):,} rows from {csv_path.name}")

    sys.path.insert(0, str(ROOT / "src" / "model"))
    from url_embeddings import URLEmbedder

    embedder = URLEmbedder().load(model_dir / "url_embedder.joblib")
    url_embed = embedder.transform(df["url_path"].fillna(""))

    import json
    with open(model_dir / "domain_encodings.json") as f:
        enc = json.load(f)
    with open(model_dir / "feature_columns.json") as f:
        feature_cols = json.load(f)

    X = build_features_full(df, enc, url_embed, feature_cols, six_type_model)

    booster = xgb.Booster()
    booster.load_model(str(model_dir / "xgb_transfer_bytes.json"))
    booster.feature_names = feature_cols
    dmat = xgb.DMatrix(X.values, feature_names=feature_cols)
    preds = np.clip(booster.predict(dmat), 0, None)
    truths = df["transfer_bytes"].values
    lut_preds = X["domain_type_median"].values

    mae = mean_absolute_error(truths, preds)
    lut_mae = mean_absolute_error(truths, lut_preds)
    rho, _ = spearmanr(truths, preds)

    # Aggregation simulation: 2000 trials at N=200 uniform
    rng = np.random.default_rng(42)
    n = len(df)
    model_pcts = np.empty(2000)
    lut_pcts = np.empty(2000)
    for t in range(2000):
        idx = rng.integers(0, n, size=200)
        true_sum = truths[idx].sum()
        if true_sum == 0: continue
        model_pcts[t] = abs(preds[idx].sum() - true_sum) / true_sum * 100
        lut_pcts[t]   = abs(lut_preds[idx].sum() - true_sum) / true_sum * 100

    return {
        "n_rows": int(len(df)),
        "model_mae": float(mae),
        "lut_mae": float(lut_mae),
        "rho": float(rho),
        "per_request_advantage_pct": float((1 - mae / lut_mae) * 100) if lut_mae > 0 else 0.0,
        "agg_model_median_pct": float(np.median(model_pcts)),
        "agg_lut_median_pct": float(np.median(lut_pcts)),
        "agg_advantage_pp": float(np.median(lut_pcts) - np.median(model_pcts)),
    }


def main():
    # June 2024 model is 6-type one-hot (the original)
    six_type = True
    print(f"Using model dir: {MODELS}  (6-type one-hot: {six_type})")

    print(f"\n{'Horizon':<18s} {'mo':>3s} {'n_rows':>10s} "
          f"{'M MAE':>9s} {'L MAE':>9s} {'PerReq':>7s} "
          f"{'Mod agg':>7s} {'LUT agg':>7s} {'AggAdv':>7s} {'rho':>6s}")
    print("-" * 100)

    results = {}
    for label, folder, fname, months in HORIZONS:
        csv_path = RAW / folder / fname
        if not csv_path.exists():
            print(f"{label:<18s} {months:>3d}  (missing CSV)")
            continue
        t0 = time.time()
        r = evaluate_csv(csv_path, MODELS, six_type_model=six_type)
        elapsed = time.time() - t0
        results[label] = r
        print(f"{label:<18s} {months:>3d} {r['n_rows']:>10,d} "
              f"{r['model_mae']:>9,.0f} {r['lut_mae']:>9,.0f} "
              f"{r['per_request_advantage_pct']:>+6.1f}% "
              f"{r['agg_model_median_pct']:>6.1f}% {r['agg_lut_median_pct']:>6.1f}% "
              f"{r['agg_advantage_pp']:>+5.1f}pp {r['rho']:>6.3f}")

    out = MODELS / "temporal_curve.json"
    import json
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
