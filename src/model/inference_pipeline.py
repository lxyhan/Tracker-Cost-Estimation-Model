"""
Inference-time pipeline: load fitted artifacts and predict transfer_bytes for a new URL.

Companion to train_multi_target.py. After training, run save_inference_artifacts()
to dump the domain target encodings + feature column order alongside the
URLEmbedder (which is already saved by train_multi_target.py via embedder.save()).

Then for inference on a new URL, use predict_url() which loads everything and
returns a single prediction.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "per_request" / "apr2026"

EMBEDDER_PATH = MODELS / "url_embedder.joblib"
ENCODINGS_PATH = MODELS / "domain_encodings.json"
FEATURE_COLS_PATH = MODELS / "feature_columns.json"
MODEL_PATH = MODELS / "xgb_transfer_bytes.json"


# ----------------------------------------------------------------------------
# Save-time helpers (called once at end of training)
# ----------------------------------------------------------------------------

def save_inference_artifacts(train_df, feature_columns, target_col="transfer_bytes"):
    """Persist domain encodings + feature column order so we can engineer
    features for new URLs at inference time without reloading the training CSV."""
    domain_medians = train_df.groupby("tracker_domain")[target_col].median().to_dict()
    domain_type_medians = train_df.groupby(
        ["tracker_domain", "resource_type"])[target_col].median().to_dict()
    global_median = float(train_df[target_col].median())
    domain_volumes = train_df.groupby("tracker_domain").size().to_dict()

    out = {
        "global_median": global_median,
        "domain_median": {str(k): float(v) for k, v in domain_medians.items()
                          if pd.notna(v)},
        # tuples can't be JSON keys; serialize as "domain||type"
        "domain_type_median": {f"{k[0]}||{k[1]}": float(v)
                               for k, v in domain_type_medians.items()
                               if pd.notna(v)},
        "domain_volume": {str(k): int(v) for k, v in domain_volumes.items()},
    }
    with open(ENCODINGS_PATH, "w") as f:
        json.dump(out, f)
    with open(FEATURE_COLS_PATH, "w") as f:
        json.dump(list(feature_columns), f)

    print(f"Saved {ENCODINGS_PATH} ({len(out['domain_median'])} domains, "
          f"{len(out['domain_type_median'])} domain+type pairs)")
    print(f"Saved {FEATURE_COLS_PATH} ({len(feature_columns)} features)")


# ----------------------------------------------------------------------------
# Inference-time helpers
# ----------------------------------------------------------------------------

def url_to_features(url: str, resource_type: str = "script",
                    initiator_type: str = "script", http_method: str = "GET",
                    http_version: str = "HTTP/2", is_https: bool = True,
                    waterfall_index: int = 10, chrome_priority: str = "Medium"):
    """Convert a raw URL + minimal request metadata into the structural features
    the model expects. Returns a dict of stateless features (everything except
    URL embedding + target encodings, which are added later)."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    query = parsed.query or ""
    full_path = path + ("?" + query if query else "")

    # File extension
    ext_match = re.search(r"\.([a-zA-Z0-9]+)(?:\?|#|$)", url)
    file_extension = ext_match.group(1).lower() if ext_match else None

    # Path depth = number of "/" segments after the host
    path_depth = path.count("/")
    url_length = len(url)
    num_query_params = len(parse_qs(query)) if query else 0
    has_query_params = bool(query)
    path_token_count = path.count("/")

    return {
        "tracker_domain": parsed.hostname or "",
        "url_path": full_path,
        "path_depth": path_depth,
        "file_extension": file_extension,
        "has_query_params": has_query_params,
        "url_length": url_length,
        "num_query_params": num_query_params,
        "resource_type": resource_type,
        "initiator_type": initiator_type,
        "chrome_priority": chrome_priority,
        "http_method": http_method,
        "http_version": http_version,
        "is_https": int(is_https),
        "waterfall_index": waterfall_index,
        "page_domain": "",  # unused at inference
    }


class InferencePipeline:
    """Loads fitted artifacts once; serves repeated predictions on new URLs."""

    def __init__(self):
        from url_embeddings import URLEmbedder

        self.embedder = URLEmbedder().load(EMBEDDER_PATH)
        with open(ENCODINGS_PATH) as f:
            self.encodings = json.load(f)
        with open(FEATURE_COLS_PATH) as f:
            self.feature_cols = json.load(f)
        self.model = xgb.Booster()
        self.model.load_model(str(MODEL_PATH))
        self.global_median = self.encodings["global_median"]

    def _engineer(self, row: dict, url_embed: np.ndarray) -> pd.DataFrame:
        """Build a single-row feature DataFrame matching training feature_cols."""
        domain = row["tracker_domain"]
        rt = row["resource_type"]
        d_med = self.encodings["domain_median"].get(domain, self.global_median)
        dt_key = f"{domain}||{rt}"
        dt_med = self.encodings["domain_type_median"].get(dt_key, d_med)
        d_vol = self.encodings["domain_volume"].get(domain, 0)

        feats = {
            "domain_median_bytes": d_med,
            "domain_type_median": dt_med,
            "domain_volume": float(np.log1p(d_vol)),
            "path_depth": row["path_depth"],
            "url_length": row["url_length"],
            "num_query_params": row["num_query_params"],
            "has_query_params": int(row["has_query_params"]),
            "path_token_count": row["url_path"].count("/"),
            "waterfall_index": row["waterfall_index"],
            "is_https": row["is_https"],
        }

        for rt_v in ["script", "image", "other", "html", "text", "json",
                     "css", "font", "video", "xml", "audio"]:
            feats[f"rt_{rt_v}"] = int(rt == rt_v)
        for it in ["script", "parser", "other", "preflight"]:
            feats[f"init_{it}"] = int(row["initiator_type"] == it)
        for m in ["GET", "POST"]:
            feats[f"method_{m}"] = int(row["http_method"] == m)
        for v in ["HTTP/2", "h3", "http/1.1"]:
            feats[f"httpv_{v}"] = int(row["http_version"] == v)
        for e in ["js", "gif", "html", "php", "jpg", "json", "png", "css",
                  "other", "none"]:
            feats[f"ext_{e}"] = int((row["file_extension"] or "none") == e)

        priority_map = {"Lowest": 0, "Low": 1, "Medium": 2, "High": 3, "Highest": 4}
        feats["priority_ord"] = priority_map.get(row["chrome_priority"], 1)

        # URL content regex flags
        path = row["url_path"]
        flags = {
            "path_has_js": r"\.js|/js/|script|sdk|lib|tag|gtm|gtag",
            "path_has_collect": r"collect|beacon|ping|pixel|track",
            "path_has_image": r"\.gif|\.png|\.jpg|pixel|1x1",
            "path_has_sync": r"sync|match|cookie|usersync",
            "path_has_ad": r"/ad/|/ads/|adserver|pagead|prebid",
            "path_has_api": r"/api/|/v[0-9]/|/collect|/event",
        }
        for name, pattern in flags.items():
            feats[name] = int(bool(re.search(pattern, path, re.I)))

        # Add URL embedding components
        for i in range(url_embed.shape[0]):
            feats[f"url_embed_{i}"] = float(url_embed[i])

        # Build DataFrame in the exact training column order; missing → 0
        row_df = pd.DataFrame([feats])
        for col in self.feature_cols:
            if col not in row_df.columns:
                row_df[col] = 0.0
        return row_df[self.feature_cols]

    def predict(self, url: str, **kwargs) -> float:
        """Predict transfer_bytes for a single URL."""
        row = url_to_features(url, **kwargs)
        url_embed = self.embedder.transform([row["url_path"]])[0]
        X = self._engineer(row, url_embed)
        dmat = xgb.DMatrix(X)
        return float(self.model.predict(dmat)[0])


def main():
    """Quick smoke test."""
    pipe = InferencePipeline()
    test_urls = [
        "https://www.googletagmanager.com/gtag/js?id=G-LF8JKE56WB",
        "https://www.google-analytics.com/collect",
        "https://connect.facebook.net/en_US/fbevents.js",
    ]
    for url in test_urls:
        pred = pipe.predict(url)
        print(f"  {pred:>10,.0f} B  {url}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
