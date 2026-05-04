-- Heavy-hitter tracker concentration: how concentrated are the bytes ETP
-- blocks across tracker domains? Quantifies "tracker ecosystem is dominated
-- by a few large players" claim. Useful for the per-category narrative in §3.
--
-- Output: data/raw/top_tracker_domains.csv (~5K rows)

WITH tracker_domains AS (
  SELECT domain FROM `httparchive.almanac.third_parties`
  WHERE date = '2024-06-01'
    AND category IN ('ad', 'analytics', 'social', 'tag-manager', 'consent-provider')
),
domain_stats AS (
  SELECT
    NET.HOST(req.url) AS tracker_domain,
    COUNT(*) AS request_count,
    SUM(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64)) AS bytes_total,
    APPROX_QUANTILES(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64), 100)[OFFSET(50)] AS bytes_p50,
    APPROX_QUANTILES(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64), 100)[OFFSET(90)] AS bytes_p90,
    COUNT(DISTINCT REGEXP_EXTRACT(req.url, r'https?://[^/]+(\/[^?#]*)')) AS distinct_paths,
  FROM `httparchive.crawl.requests` req
  WHERE req.date = '2024-06-01'
    AND req.client = 'mobile'
    AND req.is_root_page = TRUE
    AND NET.HOST(req.url) IN (SELECT domain FROM tracker_domains)
  GROUP BY tracker_domain
)
SELECT
  tracker_domain,
  request_count,
  bytes_total,
  ROUND(100.0 * request_count / SUM(request_count) OVER (), 4) AS pct_requests,
  ROUND(100.0 * bytes_total / SUM(bytes_total) OVER (), 4) AS pct_bytes,
  bytes_p50,
  bytes_p90,
  distinct_paths,
FROM domain_stats
ORDER BY bytes_total DESC
