"""
Empirical UA-conditioned byte agreement test.

For a curated list of common tracker URLs, fetch each twice (Firefox UA, Chrome UA)
and compute per-URL byte agreement. Quantifies the §3.1(iii) "bounded residual
variation" claim that user-agent content negotiation affects byte counts on a
minority of requests by small fractions.

Output: data/raw/ua_agreement.csv with per-URL fetch results, plus a printed summary.
"""

from __future__ import annotations
import csv
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "ua_agreement.csv"

UA_FIREFOX = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0"
)
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ACCEPT_FIREFOX = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
ACCEPT_CHROME = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"

# Curated tracker URLs spanning the high-traffic domains in the test set.
# Mix of script bundles (large), pixels/beacons (near-zero), and resource files.
TRACKER_URLS = [
    # Google Tag Manager / GTAG (large script bundles)
    "https://www.googletagmanager.com/gtag/js?id=G-LF8JKE56WB",
    "https://www.googletagmanager.com/gtag/js?id=GTM-NN9QGR8",
    "https://www.googletagmanager.com/gtm.js?id=GTM-WCSPZRP",
    "https://www.googletagmanager.com/gtm.js?id=GTM-N48HSDV",
    # Google Analytics (mixed: scripts + collect beacons)
    "https://www.google-analytics.com/analytics.js",
    "https://www.google-analytics.com/ga.js",
    "https://ssl.google-analytics.com/ga.js",
    "https://ssl.google-analytics.com/analytics.js",
    "https://www.google-analytics.com/plugins/ua/linkid.js",
    # Google Ad Services / DoubleClick
    "https://googleads.g.doubleclick.net/pagead/id",
    "https://stats.g.doubleclick.net/dc.js",
    "https://www.googleadservices.com/pagead/conversion.js",
    "https://www.googleadservices.com/pagead/conversion_async.js",
    "https://www.google.com/recaptcha/api.js",
    # Google Syndication (ads)
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
    "https://pagead2.googlesyndication.com/pagead/js/r20231130/r20110914/show_ads_impl.js",
    "https://tpc.googlesyndication.com/safeframe/1-0-40/html/container.html",
    # Facebook / Meta
    "https://connect.facebook.net/en_US/fbevents.js",
    "https://connect.facebook.net/en_US/sdk.js",
    "https://connect.facebook.net/signals/config/100",
    "https://connect.facebook.net/en_US/all.js",
    "https://connect.facebook.net/en_US/fbds.js",
    # Bing Ads
    "https://bat.bing.com/bat.js",
    "https://bat.bing.com/p/action/0.js",
    # LinkedIn
    "https://snap.licdn.com/li.lms-analytics/insight.min.js",
    "https://px.ads.linkedin.com/collect/",
    # Twitter / X
    "https://static.ads-twitter.com/uwt.js",
    "https://static.ads-twitter.com/oct.js",
    # Hotjar
    "https://static.hotjar.com/c/hotjar-1234.js",
    # Yandex
    "https://mc.yandex.ru/metrika/tag.js",
    "https://mc.yandex.ru/watch/100500",
    # Pinterest
    "https://s.pinimg.com/ct/core.js",
    # Adobe
    "https://assets.adobedtm.com/launch-EN.min.js",
    # TikTok
    "https://analytics.tiktok.com/i18n/pixel/sdk.js",
    "https://analytics.tiktok.com/i18n/pixel/events.js",
    # Cloudflare Insights
    "https://static.cloudflareinsights.com/beacon.min.js",
    # Snapchat
    "https://sc-static.net/scevent.min.js",
    # Reddit
    "https://www.redditstatic.com/ads/pixel.js",
    # Quantcast
    "https://secure.quantserve.com/quant.js",
    # Optimizely
    "https://cdn.optimizely.com/js/12345678.js",
    # Segment
    "https://cdn.segment.com/analytics.js/v1/analytics.min.js",
    # Mixpanel
    "https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js",
    # Heap
    "https://cdn.heapanalytics.com/js/heap.js",
    # Fullstory
    "https://edge.fullstory.com/s/fs.js",
    # Klaviyo
    "https://static.klaviyo.com/onsite/js/klaviyo.js",
    # Crazy Egg
    "https://script.crazyegg.com/pages/scripts/0124/3456.js",
    # Drift
    "https://js.driftt.com/include/1234567890/abcdef.js",
    # Intercom
    "https://widget.intercom.io/widget/abc123",
    # Tealium
    "https://tags.tiqcdn.com/utag/example/main/prod/utag.js",
    # OneTrust / cookielaw
    "https://cdn.cookielaw.org/scripttemplates/otSDKStub.js",
    # UserCentrics
    "https://app.usercentrics.eu/browser-ui/latest/loader.js",
    # Bugsnag
    "https://d2wy8f7a9ursnm.cloudfront.net/v7/bugsnag.min.js",
    # New Relic
    "https://js-agent.newrelic.com/nr-1234.min.js",
    # Datadog RUM
    "https://www.datadoghq-browser-agent.com/datadog-rum.js",
]


def make_session(ua: str, accept: str) -> requests.Session:
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5,
                    status_forcelist=[502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": ua,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",  # disable compression so byte counts are comparable
        "Connection": "close",
    })
    return s


def fetch_one(session: requests.Session, url: str, timeout: float = 8.0) -> tuple[int | None, int | None, str]:
    """Returns (status_code, content_bytes, error)."""
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        return (r.status_code, len(r.content), "")
    except Exception as e:
        return (None, None, str(e)[:80])


def main():
    ff = make_session(UA_FIREFOX, ACCEPT_FIREFOX)
    ch = make_session(UA_CHROME, ACCEPT_CHROME)

    rows = []
    for i, url in enumerate(TRACKER_URLS):
        ff_status, ff_bytes, ff_err = fetch_one(ff, url)
        time.sleep(0.05)
        ch_status, ch_bytes, ch_err = fetch_one(ch, url)
        time.sleep(0.05)
        rows.append({
            "url": url,
            "ff_status": ff_status, "ff_bytes": ff_bytes, "ff_err": ff_err,
            "ch_status": ch_status, "ch_bytes": ch_bytes, "ch_err": ch_err,
        })
        marker = "OK" if ff_status == 200 and ch_status == 200 else "skip"
        print(f"[{i+1:3d}/{len(TRACKER_URLS)}] {marker:4s} ff={ff_status} {ff_bytes} ch={ch_status} {ch_bytes} {url[:60]}",
              flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Aggregate
    pairs_ok = [r for r in rows if r["ff_status"] == 200 and r["ch_status"] == 200
                and r["ff_bytes"] is not None and r["ch_bytes"] is not None]
    print(f"\n=== Summary ===")
    print(f"URLs attempted: {len(rows)}")
    print(f"Both fetches succeeded (200/200): {len(pairs_ok)}")

    if not pairs_ok:
        print("No successful pairs; nothing to aggregate.")
        return

    ratios = []
    abs_diffs = []
    for r in pairs_ok:
        ff, ch = r["ff_bytes"], r["ch_bytes"]
        if max(ff, ch) == 0:
            ratios.append(1.0)
        else:
            ratios.append(min(ff, ch) / max(ff, ch))
        abs_diffs.append(abs(ff - ch))

    ratios.sort()
    abs_diffs.sort()
    n = len(ratios)
    median_ratio = ratios[n // 2]
    p10_ratio = ratios[n // 10] if n >= 10 else ratios[0]
    within_5pct = sum(1 for r in ratios if r >= 0.95) / n
    within_10pct = sum(1 for r in ratios if r >= 0.90) / n
    within_50pct = sum(1 for r in ratios if r >= 0.50) / n
    substantial_div = sum(1 for r in ratios if r < 0.5) / n
    median_abs_diff = abs_diffs[n // 2]
    p90_abs_diff = abs_diffs[int(0.9 * n)] if n >= 10 else abs_diffs[-1]

    print(f"Median byte ratio (Firefox vs Chrome): {median_ratio:.4f}  (1.0 = identical)")
    print(f"p10 byte ratio:                        {p10_ratio:.4f}")
    print(f"Fraction within 5%:                    {within_5pct*100:.1f}%")
    print(f"Fraction within 10%:                   {within_10pct*100:.1f}%")
    print(f"Fraction within 50%:                   {within_50pct*100:.1f}%")
    print(f"Fraction with substantial divergence (<50% agreement): {substantial_div*100:.1f}%")
    print(f"Median absolute byte diff:             {median_abs_diff} B")
    print(f"p90 absolute byte diff:                {p90_abs_diff} B")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
