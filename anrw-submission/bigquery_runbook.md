# BigQuery Runbook — pulling per-request data

For the full methodology re-run + the bonus measurement experiments. All queries use the public `httparchive.crawl.requests` table; no special access needed. Cost is ~$1-5 per query at 1% sampling, ~$0.50 for the small aggregation queries.

---

## Tier A: Required for paper retraining

### Query 1: June 2024 (TRAINING DATA — required)

`sql/05_per_request_full.sql` → save Drive output as `per_request_full.csv` → place in `data/raw/`.

Expected: ~3.5M rows.

This is the ONLY query that's strictly required. Everything below is bonus.

---

## Tier B: Temporal-degradation curve (the supervisor flagged "longer horizons unmeasured" — this nukes that)

Pull these to build a 4-point degradation curve: 1, 3, 6, 12 months from the June training set. Reviewers love a real degradation curve.

| File | Date | Horizon | Output CSV |
|---|---|---|---|
| `sql/08_temporal_jul2024.sql` | 2024-07-01 | 1 month | `data/raw/per_request_1pct_jul2024.csv` |
| `sql/07_temporal_holdout.sql` | 2024-09-01 | 3 months | `data/raw/per_request_1pct_sep2024.csv` |
| `sql/09_temporal_dec2024.sql` | 2024-12-01 | 6 months | `data/raw/per_request_1pct_dec2024.csv` |
| `sql/10_temporal_jun2025.sql` | 2025-06-01 | 12 months | `data/raw/per_request_1pct_jun2025.csv` |

Each ~1-3 min query, ~$1-3 cost. Run as many as you want; even just adding 6-month and 12-month converts the temporal claim from "limited horizon" to "characterized over a full year."

---

## Tier C: Cross-cutting validation queries (each plugs a specific supervisor-flagged hole)

| File | What it tests | Plugs |
|---|---|---|
| `sql/11_desktop_jun2024.sql` | Cross-device: same date and tracker-set, but desktop crawl instead of mobile | Cross-vantage concern. Lets us measure mobile vs desktop byte agreement at scale. |
| `sql/12_per_page_bytes.sql` | Per-page bandwidth distribution (~5M page-level rows) | Adds a user-relevant statistic the New Tab widget would actually surface |
| `sql/13_top_tracker_concentration.sql` | Heavy-hitter tracker concentration (top-N domains by bytes) | Strengthens the per-category narrative — quantifies how concentrated the tracker ecosystem is |
| `sql/14_within_domain_path_diversity.sql` | URL-path overlap between June and other months | Underpins the "URL space churns continuously" claim with multi-month data |
| `sql/15_per_category_full_population.sql` | Per-category cost share at full population, using HTTP Archive's native categories | Cross-checks Table 1 with an independent computation; defuses "those categories don't match what ETP uses" |
| `sql/16_sample_stability.sql` | Two independent 1% samples, compared head-to-head | Defends "1% sample is representative" against cherry-picking concerns |

---

## Console steps (Path 2: Save to Drive)

For each query:

1. Open `console.cloud.google.com/bigquery`
2. Pick a billing project
3. Paste the query into the editor
4. Click **Run**
5. After result appears: **Save Results** → **Google Drive (CSV)**
6. Wait for the export job notification
7. Download from Drive
8. Move/rename to the path in the table above

---

## Recommended execution order

If you have 30 minutes:
- Tier A (required) only

If you have 1 hour:
- Tier A + 6-month and 12-month from Tier B (`sql/09`, `sql/10`)
- Plus `sql/15` (per-category full-pop, fast small query)

If you have 2+ hours:
- All of Tier A + Tier B + Tier C

The small aggregation queries (`sql/12`, `sql/13`, `sql/14`, `sql/15`, `sql/16`) are tiny and fast (~30 sec each). The per-request data queries (`sql/05`, `sql/07-11`) are the heavy ones (~1-3 min each).

---

## After CSVs land — single command for retraining

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib \
python3 src/model/train_multi_target.py \
  --data data/raw/per_request_full.csv \
  --targets transfer_bytes
```

Produces:
- `models/per_request/url_embedder.joblib`
- `models/per_request/domain_encodings.json`
- `models/per_request/feature_columns.json`
- `models/per_request/xgb_transfer_bytes.json`
- `models/per_request/multi_target_results.json`

Then for Claim B (model predictions vs Firefox-fetched bytes):

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib \
python3 src/claim_b_validation.py
```

For temporal-curve evaluation across all the additional months:

```bash
# (script TBD; will be temporal_curve.py — loads model + each holdout CSV,
#  reports MAE per horizon)
```

---

## Cost / time budget

| Tier | Time | Cost |
|---|---|---|
| Tier A only | 5-10 min | ~$1-3 |
| Tier A + temporal curve (Tier B all) | 30-45 min | ~$5-15 |
| All tiers | 60-90 min | ~$10-25 |

---

## Notes

- All Tier B and C queries reference the SAME June 2024 third-party entity table for tracker classification. This is intentional — it's the same domain set the model was trained against, ensuring temporal/cross-device evaluations test only the time/device axis, not categorization shift.
- The Disconnect-list-based domain classification we use locally (`data/external/disconnect_domains.csv`) and HTTP Archive's `third_parties.category` are both proxies for the same upstream tracker ecosystem; `sql/15` directly compares them.
- Sample stability (`sql/16`) returns a tiny summary (4 rows) and is essentially free — worth running as a "did anything weird happen with sampling" gut-check.
