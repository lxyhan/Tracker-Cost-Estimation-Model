"""
Claim B v2: cleaned-input deployment validation.

Differences from the prior version:
1. Domain filter restricted to Disconnect categories the model was actually
   trained on (Advertising, Analytics, Social, ConsentManagers, plus manual
   Tag-manager additions). Excludes Content/Fingerprinting/Email/etc. that
   the model never saw in training.
2. Resource-type comes from Playwright's per-request resource_type capture
   (Firefox's own ContentPolicyType classification), not a mime-string guess.
   Mapped to the model's training-time category set.

This makes the test what production would actually do: feed the model
clean, correctly-typed features for URLs Firefox would actually block.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HAR_DIR = ROOT / "data" / "raw" / "firefox_crawl"
DISCONNECT = ROOT / "data" / "external" / "disconnect_domains.csv"
OUT_CSV = ROOT / "data" / "raw" / "claim_b_in_page_validation.csv"

# Disconnect categories the model trained on (mapped to HTTP Archive's
# 'ad', 'analytics', 'social', 'tag-manager', 'consent-provider')
TRAINED_CATEGORIES = {"Advertising", "Analytics", "Social", "ConsentManagers"}

# Manual additions for tag managers Disconnect treats as infrastructure
# (matches the per-category table in §3)
MANUAL_TAG_MANAGERS = {
    "googletagmanager.com", "googletagservices.com", "tagcommander.com",
    "ensighten.com", "tealiumiq.com", "adobedtm.com",
}

# Playwright resource_type → model's training-time req.type vocabulary.
# Model now one-hots all 11 HTTP Archive req.type values:
# {script, image, other, html, text, json, css, font, video, xml, audio}
# Each Playwright type maps to its closest HTTP Archive equivalent so that
# the same rt_* flag the model trained on fires at inference time.
PW_TO_MODEL_TYPE = {
    "script": "script",
    "image": "image",
    "document": "html",
    "stylesheet": "css",
    "font": "font",
    "media": "video",       # video/audio both possible; video is the dominant case
    "xhr": "json",          # XHR/fetch returning structured data → 'json'
    "fetch": "json",
    "eventsource": "json",
    "websocket": "other",
    "manifest": "json",
    "texttrack": "text",
    "beacon": "other",      # explicit beacons (small) → 'other'
    "ping": "other",
    "other": "other",
}


def load_trained_tracker_set() -> set:
    """Disconnect domains in categories the model was trained on, plus
    manual tag-manager additions."""
    cats = pd.read_csv(DISCONNECT)
    keep = cats[cats["category"].isin(TRAINED_CATEGORIES)]
    domains = set(keep["domain"].dropna().str.lower())
    domains.update(MANUAL_TAG_MANAGERS)
    return domains


def is_tracker_domain(host: str, tracker_set: set) -> bool:
    parts = host.split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in tracker_set:
            return True
    return False


def load_type_log(types_path: Path) -> dict:
    """URL → list of (resource_type) for that URL in this page's crawl.
    Returns first occurrence's type per URL."""
    if not types_path.exists():
        return {}
    with open(types_path) as f:
        log = json.load(f)
    out = {}
    for entry in log:
        url = entry.get("url")
        if url and url not in out:
            out[url] = entry.get("resource_type", "other")
    return out


def refine_model_type(pw_type: str, mime: str) -> str:
    """Disambiguate ambiguous Playwright types using HAR's MIME header.

    Specifically: `media` could be video or audio; sniff Content-Type to pick.
    Also handle xhr/fetch returning xml or text instead of json.
    """
    base = PW_TO_MODEL_TYPE.get(pw_type, "other")
    if not mime:
        return base
    m = mime.lower()
    if pw_type == "media":
        if m.startswith("audio/"):
            return "audio"
        if m.startswith("video/"):
            return "video"
        # default keeps the table mapping
    elif pw_type in ("xhr", "fetch"):
        if "xml" in m:
            return "xml"
        if m.startswith("text/") and "json" not in m:
            return "text"
        # default → json (table mapping)
    elif pw_type == "other":
        # Playwright's catch-all; sniff MIME for known categories
        if m.startswith("image/"):
            return "image"
        if m.startswith("font/") or "font" in m:
            return "font"
        if m.startswith("video/"):
            return "video"
        if m.startswith("audio/"):
            return "audio"
    return base


def extract_tracker_requests(har_path: Path, types_path: Path,
                             tracker_set: set, page_url: str):
    with open(har_path) as f:
        har = json.load(f)
    types = load_type_log(types_path)
    out = []
    for entry in har.get("log", {}).get("entries", []):
        req_url = entry.get("request", {}).get("url", "")
        if not req_url.startswith("http"):
            continue
        host = urlparse(req_url).hostname or ""
        if not is_tracker_domain(host.lower(), tracker_set):
            continue
        resp = entry.get("response", {})
        if resp.get("status", 0) != 200:
            continue
        ts = resp.get("_transferSize") or resp.get("bodySize") or 0
        if ts <= 0:
            continue
        pw_type = types.get(req_url, "other")
        mime = resp.get("content", {}).get("mimeType", "") or ""
        model_type = refine_model_type(pw_type, mime)
        out.append({
            "page": page_url,
            "url": req_url,
            "host": host,
            "transfer_bytes": int(ts),
            "playwright_type": pw_type,
            "mime": mime,
            "model_type": model_type,
            "method": entry.get("request", {}).get("method", "GET"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--har-dir", default=str(HAR_DIR),
                    help="Directory of HAR files (default: data/raw/firefox_crawl).")
    ap.add_argument("--out", default=str(OUT_CSV),
                    help="Output CSV path (default: data/raw/claim_b_in_page_validation.csv).")
    args = ap.parse_args()
    har_dir = Path(args.har_dir)
    out_csv = Path(args.out)

    sys.path.insert(0, str(ROOT / "src" / "model"))
    from inference_pipeline import InferencePipeline

    print("Loading trained-tracker set (Advertising/Analytics/Social/Consent + tag mgrs)...")
    tracker_set = load_trained_tracker_set()
    print(f"  {len(tracker_set):,} domains")

    print("Loading inference pipeline...")
    pipe = InferencePipeline()
    print(f"  feature_cols: {len(pipe.feature_cols)}")
    print(f"  domains in encoding: {len(pipe.encodings['domain_median']):,}")

    print(f"\nScanning HARs in {har_dir}...")
    har_files = sorted(har_dir.glob("har_*.json"))
    print(f"  {len(har_files)} HAR files")

    all_reqs = []
    for hp in har_files:
        slug = hp.stem.replace("har_", "")
        types_path = har_dir / f"types_{slug}.json"
        # Recover page host from the HAR slug: slug = "NNNN_<host>"
        # so the part after the first "_" is the URL-derived host (with
        # path separators replaced by "_"). Take everything up to the
        # next "_" as the host (works for all simple-root targets).
        slug_parts = slug.split("_", 1)
        page_host = slug_parts[1] if len(slug_parts) > 1 else ""
        # Strip trailing path remnants (host_path → host)
        page_host = page_host.split("_")[0]
        page_url = f"https://{page_host}/"
        reqs = extract_tracker_requests(hp, types_path, tracker_set, page_url)
        # Drop first-party requests: tracker request whose host shares
        # the page host's eTLD+1 is not actually a third-party tracker.
        def _share_etld1(a: str, b: str) -> bool:
            ap = a.split(".")
            bp = b.split(".")
            if len(ap) < 2 or len(bp) < 2:
                return a == b
            return ".".join(ap[-2:]) == ".".join(bp[-2:])
        before = len(reqs)
        reqs = [r for r in reqs if not _share_etld1(r["host"], page_host)]
        dropped = before - len(reqs)
        all_reqs.extend(reqs)
        print(f"  {hp.name}: {len(reqs)} third-party tracker requests "
              f"(dropped {dropped} first-party)")

    if not all_reqs:
        print("\nNo tracker requests found.")
        return

    df = pd.DataFrame(all_reqs)
    print(f"\nTotal requests after category filter: {len(df):,}")
    print(f"Unique tracker domains: {df['host'].nunique()}")
    print(f"Resource type distribution (Playwright):")
    print(df['playwright_type'].value_counts().head(10).to_string())
    print(f"\nResource type distribution (model-mapped):")
    print(df['model_type'].value_counts().to_string())

    print("\nRunning model predictions with cleaned inputs...")
    preds = []
    for _, row in df.iterrows():
        try:
            p = pipe.predict(row["url"], resource_type=row["model_type"],
                             http_method=row["method"])
        except Exception:
            p = np.nan
        preds.append(p)
    df["model_pred"] = preds
    df = df[df["model_pred"].notna()].copy()
    df["abs_err"] = (df["model_pred"] - df["transfer_bytes"]).abs()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"  Wrote {out_csv}")

    mae = df["abs_err"].mean()
    medae = df["abs_err"].median()
    spear = df[["model_pred", "transfer_bytes"]].rank().corr().iloc[0, 1]
    within_50pct = ((df["abs_err"] <= 0.5 * df["transfer_bytes"]) |
                    (df["abs_err"] <= 100)).mean()
    within_2x = (
        np.maximum(df["model_pred"], df["transfer_bytes"]) <=
        2 * np.maximum(np.minimum(df["model_pred"], df["transfer_bytes"]), 1)
    ).mean()

    print(f"\n=== Claim B v2 (cleaned inputs, in-page Firefox) ===")
    print(f"  N tracker requests:           {len(df):,}")
    print(f"  Pages crawled:                {df['page'].nunique()}")
    print(f"  Tracker domains hit:          {df['host'].nunique()}")
    print(f"  Mean transfer (truth):        {df['transfer_bytes'].mean():>10,.0f} B")
    print(f"  Median transfer (truth):      {df['transfer_bytes'].median():>10,.0f} B")
    print(f"  Mean prediction:              {df['model_pred'].mean():>10,.0f} B")
    print(f"  MAE:                          {mae:>10,.0f} B")
    print(f"  Median absolute error:        {medae:>10,.0f} B")
    print(f"  Spearman rho:                 {spear:>10.4f}")
    print(f"  Fraction within 50% / 2x:     {within_50pct*100:.1f}% / {within_2x*100:.1f}%")
    print(f"\n  Test-set MAE (in-distribution):  4,274")
    print(f"  Deployment MAE (this test):      {mae:,.0f}")
    print(f"  Ratio:                            {mae/4274:.2f}x")


if __name__ == "__main__":
    main()
