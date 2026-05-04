-- Per-page tracker bandwidth: how many bytes does ETP block per page load?
-- A user-relevant statistic at the granularity the New Tab privacy widget
-- would actually report ("Firefox saved you X bytes on this page").
-- Distribution across pages tells us what the deployment-side numbers look
-- like for real browsing.
--
-- Output: data/raw/per_page_tracker_bytes.csv (~5M rows; one per crawled page)

WITH tracker_domains AS (
  SELECT domain FROM `httparchive.almanac.third_parties`
  WHERE date = '2024-06-01'
    AND category IN ('ad', 'analytics', 'social', 'tag-manager', 'consent-provider')
)
SELECT
  NET.HOST(req.page) AS page_domain,
  req.page AS page_url,
  COUNT(*) AS tracker_request_count,
  SUM(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64)) AS tracker_bytes_total,
  AVG(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64)) AS tracker_bytes_avg,
  COUNTIF(req.type = 'script') AS tracker_scripts,
  COUNTIF(req.type = 'image') AS tracker_pixels,
  COUNT(DISTINCT NET.HOST(req.url)) AS distinct_tracker_domains,
FROM `httparchive.crawl.requests` req
WHERE req.date = '2024-06-01'
  AND req.client = 'mobile'
  AND req.is_root_page = TRUE
  AND NET.HOST(req.url) IN (SELECT domain FROM tracker_domains)
GROUP BY page_domain, page_url
HAVING tracker_request_count >= 1
