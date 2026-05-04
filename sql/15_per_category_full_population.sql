-- Per-category cost share at full population (no 1% sample) using HTTP
-- Archive's third-party entity table directly. The table in §3.3 of the
-- paper is currently computed by joining a Disconnect-categorized domain
-- list to per-domain aggregates from request_features_agg.csv. This query
-- recomputes the same numbers from HTTP Archive's native categorization at
-- full population, providing an authoritative cross-check.
--
-- Output: data/raw/per_category_authoritative.csv (5-7 rows)

WITH tracker_classification AS (
  SELECT domain, category
  FROM `httparchive.almanac.third_parties`
  WHERE date = '2024-06-01'
    AND category IN ('ad', 'analytics', 'social', 'tag-manager', 'consent-provider')
),
per_request AS (
  SELECT
    t.category,
    NET.HOST(req.url) AS tracker_domain,
    CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64) AS bytes,
  FROM `httparchive.crawl.requests` req
  JOIN tracker_classification t
    ON NET.HOST(req.url) = t.domain
  WHERE req.date = '2024-06-01'
    AND req.client = 'mobile'
    AND req.is_root_page = TRUE
)
SELECT
  category,
  COUNT(*) AS request_count,
  COUNT(DISTINCT tracker_domain) AS distinct_domains,
  SUM(bytes) AS bytes_total,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_requests,
  ROUND(100.0 * SUM(bytes) / SUM(SUM(bytes)) OVER (), 2) AS pct_bytes,
  APPROX_QUANTILES(bytes, 100)[OFFSET(50)] AS bytes_p50,
  APPROX_QUANTILES(bytes, 100)[OFFSET(90)] AS bytes_p90,
FROM per_request
WHERE bytes IS NOT NULL
GROUP BY category
ORDER BY bytes_total DESC
