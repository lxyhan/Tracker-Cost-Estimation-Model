-- Within-domain URL-path diversity over time: quantifies how fast the URL
-- space churns. Underpins the "URL space changes continuously" claim that
-- motivates the model over the path LUT.
--
-- Reports per-domain: number of distinct URL paths in each crawl month
-- and the Jaccard overlap between June and other months. Low overlap →
-- path LUT staleness; supports the temporal-degradation explanation.
--
-- Output: data/raw/path_diversity_jun_vs_others.csv (one row per domain × month)

WITH tracker_domains AS (
  SELECT domain FROM `httparchive.almanac.third_parties`
  WHERE date = '2024-06-01'
    AND category IN ('ad', 'analytics', 'social', 'tag-manager', 'consent-provider')
),
paths_per_domain_per_month AS (
  SELECT
    DATE(req.date) AS crawl_date,
    NET.HOST(req.url) AS tracker_domain,
    REGEXP_EXTRACT(req.url, r'https?://[^/]+(\/[^?#]*)') AS url_path,
  FROM `httparchive.crawl.requests` req
  WHERE req.date IN ('2024-06-01', '2024-07-01', '2024-09-01', '2024-12-01', '2025-06-01')
    AND req.client = 'mobile'
    AND req.is_root_page = TRUE
    AND NET.HOST(req.url) IN (SELECT domain FROM tracker_domains)
  GROUP BY crawl_date, tracker_domain, url_path
),
june_paths AS (
  SELECT tracker_domain, ARRAY_AGG(DISTINCT url_path IGNORE NULLS) AS paths
  FROM paths_per_domain_per_month
  WHERE crawl_date = '2024-06-01'
  GROUP BY tracker_domain
),
other_month_paths AS (
  SELECT crawl_date, tracker_domain, ARRAY_AGG(DISTINCT url_path IGNORE NULLS) AS paths
  FROM paths_per_domain_per_month
  WHERE crawl_date != '2024-06-01'
  GROUP BY crawl_date, tracker_domain
)
SELECT
  o.crawl_date,
  o.tracker_domain,
  ARRAY_LENGTH(j.paths) AS jun_distinct_paths,
  ARRAY_LENGTH(o.paths) AS other_distinct_paths,
  (SELECT COUNT(*) FROM UNNEST(j.paths) p WHERE p IN UNNEST(o.paths)) AS shared_paths,
  ROUND(SAFE_DIVIDE(
    (SELECT COUNT(*) FROM UNNEST(j.paths) p WHERE p IN UNNEST(o.paths)),
    ARRAY_LENGTH(o.paths)
  ), 4) AS pct_in_june,  -- fraction of other-month paths seen in June
FROM other_month_paths o
JOIN june_paths j USING (tracker_domain)
WHERE ARRAY_LENGTH(o.paths) >= 5  -- noise filter
ORDER BY o.crawl_date, jun_distinct_paths DESC
