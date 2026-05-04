# Experiment 01 — Per-category cost-share table

## Goal

Fill `Table~\ref{tab:per-category}` (currently `[PLACEHOLDER]` at `paper.tex:161-177`) with real numbers: for each of the five tracker categories (advertising, analytics, social, tag-manager, consent-provider), report % of blocked requests, % of blocked transfer bytes, and median bytes per request.

## Why this matters

This is the single most ANRW-flavored measurement in the paper. ANRW reviewers reward concrete per-category numbers from a deployed system. The "tag-manager and advertising dominate bytes despite being a minority of requests" finding is what differentiates this from page-level measurements like Brave. Cannot ship as XX.X — either real or cut.

## Paper hole

- `anrw-submission/paper.tex:155-159`: prose claims "tag-manager and advertising domains together account for the majority of blocked transfer bytes despite being a minority of blocked requests" — currently unsupported.
- `anrw-submission/paper.tex:161-177`: 5-row × 3-column table with all cells `XX.X` / `XXX`.

## Inputs

- HTTP Archive June 2024 mobile crawl: `httparchive.crawl.requests` (date `2024-06-01`, client `mobile`, `is_root_page = TRUE`).
- Third-party entity classification: `httparchive.almanac.third_parties` (date `2024-06-01`, `category IN ('ad', 'analytics', 'social', 'tag-manager', 'consent-provider')`).
- Existing SQL pattern at `sql/05_per_request_full.sql` (already filters this set).

## Method

1. Write `sql/08_per_category_aggregates.sql` adapting the WHERE clause from `sql/05_per_request_full.sql` but **without the 1% sample filter** (we want population aggregates, not the modeling sample).
2. Group by `t.category`, aggregate:
   - `request_count = COUNT(*)`
   - `byte_total = SUM(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64))`
   - `byte_median = APPROX_QUANTILES(CAST(JSON_VALUE(req.payload, '$._bytesIn') AS INT64), 100)[OFFSET(50)]`
3. In a window over all categories, compute share columns:
   - `pct_requests = request_count / SUM(request_count) OVER ()`
   - `pct_bytes = byte_total / SUM(byte_total) OVER ()`
4. Run via `bq query --use_legacy_sql=false < sql/08_per_category_aggregates.sql > data/raw/per_category.csv`.
5. Format into LaTeX rows.

## Expected output

Replace `paper.tex:161-177` block with the populated table, drop the `[PLACEHOLDER]` marker, and rewrite the caption to remove the placeholder warning. Final form:

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrr}
\toprule
Category & \% requests & \% bytes & Median bytes \\
\midrule
Advertising      & XX.X & XX.X & XXX \\   % ← replace with computed values
Analytics        & XX.X & XX.X & XXX \\
Tag-manager      & XX.X & XX.X & XXX \\
Social           & XX.X & XX.X & XXX \\
Consent-provider & XX.X & XX.X & XXX \\
\bottomrule
\end{tabular}
\caption{Per-category share of blocked tracker traffic (HTTP Archive June 2024 mobile crawl). Bytes are concentrated in fewer categories than requests because a high-byte minority (script bundles in tag-manager and advertising) drives the aggregate.}
\label{tab:per-category}
\end{table}
```

Also rewrite the prose at `paper.tex:155-159` to cite the actual numbers (e.g., "tag-manager and advertising together account for X.X% of blocked bytes despite being only Y.Y% of blocked requests").

## Effort

~2 hrs:
- 30 min: write SQL + dry-run on small date range
- 30 min: full run (BigQuery cost: maybe $1-5 depending on column scan)
- 30 min: format LaTeX, rewrite prose
- 30 min: buffer for SQL debugging

## Risks / blockers

- **BigQuery access.** Requires authenticated `bq` CLI with billing project. Confirm `bq query 'SELECT 1'` works before scheduling.
- **Cost.** `httparchive.crawl.requests` is large; full month scan can be expensive. Mitigate by selecting only needed columns, filtering early, and using `--maximum_bytes_billed`.
- **Null bytes.** Some requests have null `_bytesIn`; filter `WHERE CAST(JSON_VALUE(...) AS INT64) IS NOT NULL` for byte aggregations.

## Fallback if blocked

Cut Table 1 entirely. Replace §3.3 ("Per-category cost share") with one prose paragraph that names the qualitative finding without numbers ("tracker categories contribute unequally to blocked bandwidth: high-byte categories like tag-manager and advertising dominate bytes despite being a minority of requests, while analytics and social are dominated by near-zero beacons"). Acknowledge in §10 limitations that per-category quantification is left to future work.

This is a real loss — the per-category table is the most ANRW-quotable artifact in the paper.

## Done when

- [ ] `sql/08_per_category_aggregates.sql` exists and runs
- [ ] `data/raw/per_category.csv` exists with 5 rows
- [ ] `Table~\ref{tab:per-category}` populated, `[PLACEHOLDER]` removed
- [ ] Prose at `paper.tex:155-159` cites the computed numbers
- [ ] PDF compiles, table renders, no overfull boxes
