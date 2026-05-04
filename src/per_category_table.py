"""
Per-category cost-share table for ANRW paper §3.

Joins per-domain aggregates (request_features_agg.csv, full population) to
Disconnect categories (with priority resolution for multi-category domains)
plus manual additions for high-traffic unmatched domains (googletagmanager etc.).

Output: data/raw/per_category.csv and a LaTeX-ready table to stdout.
"""

import pandas as pd
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGG = ROOT / "data" / "raw" / "request_features_agg.csv"
CATS = ROOT / "data" / "external" / "disconnect_domains.csv"
OUT = ROOT / "data" / "raw" / "per_category.csv"

# Disconnect priority for canonical category. Lower index = higher priority.
# Reflects "what is this domain primarily for?"
PRIORITY = [
    "Advertising",
    "Social",
    "ConsentManagers",
    "Analytics",
    "FingerprintingInvasive",
    "FingerprintingGeneral",
    "Anti-fraud",
    "Cryptomining",
    "Content",
    "EmailAggressive",
    "Email",
]

# Manual additions for high-traffic domains absent from Disconnect (Disconnect
# treats Google's tag-management infrastructure as non-tracker; HTTP Archive's
# third_parties table classifies it as "tag-manager"). All entries verified by
# inspection of the unmatched top-traffic list.
MANUAL = {
    "googletagmanager.com": "TagManager",
    "googletagservices.com": "TagManager",
    "tagcommander.com": "TagManager",
    "ensighten.com": "TagManager",
    "tealiumiq.com": "TagManager",
    "adobedtm.com": "TagManager",
    "usercentrics.eu": "ConsentManagers",
    "cookielaw.org": "ConsentManagers",
}

# Display labels and ordering for the final table.
DISPLAY = {
    "Advertising": "Advertising",
    "TagManager": "Tag manager",
    "Social": "Social",
    "Analytics": "Analytics",
    "FingerprintingGeneral": "Fingerprinting",
    "FingerprintingInvasive": "Fingerprinting",
    "ConsentManagers": "Consent provider",
    "Content": "Content (CDN)",
    "Anti-fraud": "Other",
    "Cryptomining": "Other",
    "Email": "Other",
    "EmailAggressive": "Other",
}


def canonical_category_map() -> dict:
    """For each domain in disconnect_domains.csv, pick canonical category by priority."""
    cats = pd.read_csv(CATS)
    by_domain = defaultdict(set)
    for _, row in cats.iterrows():
        if pd.notna(row["domain"]) and pd.notna(row["category"]):
            by_domain[row["domain"]].add(row["category"])

    rank = {c: i for i, c in enumerate(PRIORITY)}

    def pick(cat_set: set) -> str:
        return min(cat_set, key=lambda c: rank.get(c, len(rank)))

    canonical = {d: pick(s) for d, s in by_domain.items()}
    canonical.update(MANUAL)
    return canonical


def find_category(domain, lookup):
    """Suffix-walk: try domain, then strip leading subdomains until match."""
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in lookup:
            return lookup[candidate]
    return None


def main():
    agg = pd.read_csv(AGG)
    agg["total_bytes"] = agg["total_requests"] * agg["mean_transfer_bytes"]

    lookup = canonical_category_map()
    agg["raw_category"] = agg["tracker_domain"].map(lambda d: find_category(d, lookup))
    agg["display_category"] = agg["raw_category"].map(lambda c: DISPLAY.get(c, "Other"))
    agg.loc[agg["raw_category"].isna(), "display_category"] = "Other"

    matched = agg["raw_category"].notna().sum()
    print(f"Matched {matched} of {len(agg)} domains ({matched/len(agg)*100:.1f}%)")
    print(f"Matched share of requests: {agg.loc[agg['raw_category'].notna(), 'total_requests'].sum() / agg['total_requests'].sum() * 100:.1f}%")
    print(f"Matched share of bytes:    {agg.loc[agg['raw_category'].notna(), 'total_bytes'].sum() / agg['total_bytes'].sum() * 100:.1f}%")

    g = agg.groupby("display_category").agg(
        n_domains=("tracker_domain", "count"),
        requests=("total_requests", "sum"),
        bytes_=("total_bytes", "sum"),
        median_p50=("p50_transfer_bytes", "median"),
    )
    g["pct_requests"] = 100 * g["requests"] / g["requests"].sum()
    g["pct_bytes"] = 100 * g["bytes_"] / g["bytes_"].sum()
    g = g.sort_values("pct_bytes", ascending=False)

    print("\n=== Per-category breakdown ===")
    cols = ["n_domains", "pct_requests", "pct_bytes", "median_p50"]
    print(g[cols].round(2).to_string())
    print(f"\nTotal requests: {g['requests'].sum()/1e9:.2f}B")
    print(f"Total bytes:    {g['bytes_'].sum()/1e12:.2f}TB")

    out = g[cols].reset_index()
    out.columns = ["category", "n_domains", "pct_requests", "pct_bytes", "median_bytes"]
    out.to_csv(OUT, index=False)
    print(f"\nWrote {OUT}")

    print("\n=== LaTeX rows (paste into tab:per-category) ===")
    order = ["Tag manager", "Advertising", "Fingerprinting", "Social",
             "Analytics", "Consent provider", "Content (CDN)", "Other"]
    for cat in order:
        if cat in g.index:
            r = g.loc[cat]
            median = int(r["median_p50"])
            print(f"{cat:18s} & {int(r['n_domains']):5d} & {r['pct_requests']:5.1f} & {r['pct_bytes']:5.1f} & {median:6d} \\\\")


if __name__ == "__main__":
    main()
