# Full Methodology Re-Run Plan — 2026-05-03

**Goal.** Re-run every experiment in the paper end-to-end with a freshly pulled dataset. Produces:
- Validated paper numbers (small drift from random-seed / SVD-fit differences expected)
- Fitted feature pipeline artifacts saved to disk (so we can engineer features for new URLs → enables Claim B)
- Fully reproducible artifact for submission

**Estimated total: 3-4 hours** (faster than building from scratch because the existing codebase has the experiments already coded).

---

## Phase 1 — Data acquisition (~30 min, gated on user)

**Owner: user.** Needs BigQuery / gcloud auth. Then:

1. `gcloud auth application-default login` (if not done)
2. `gcloud config set project <PROJECT_ID>` (BigQuery-enabled project)
3. From repo root, run the query:
   ```
   bq query --use_legacy_sql=false --format=csv --max_rows=10000000 \
     "$(cat sql/05_per_request_full.sql)" > data/raw/per_request_full.csv
   ```
4. Optionally pull September temporal-holdout data:
   ```
   bq query --use_legacy_sql=false --format=csv --max_rows=10000000 \
     "$(cat sql/07_temporal_holdout.sql)" > data/raw/per_request_1pct_sep2024.csv
   ```

**Cost.** ~$5-30 depending on column scan; mitigate with `--maximum_bytes_billed=50000000000` (50 GB cap).

**Done when:** `data/raw/per_request_full.csv` exists with ~3.5M rows.

---

## Phase 2 — Train + save pipeline (~30-40 min)

Modify `src/model/train_per_request.py` to:
- **Skip Optuna search** (use known-good hyperparameters: `n_estimators=500, max_depth=8, learning_rate=0.05, objective="reg:tweedie", tweedie_variance_power=1.5, subsample=0.8, colsample_bytree=0.7, min_child_weight=10`)
- **Save fitted pipeline artifacts:**
  - TF-IDF vocabulary → `models/per_request/tfidf_vocab.json`
  - SVD projection matrix → `models/per_request/svd_components.npy`
  - Domain target encodings → `models/per_request/domain_encodings.json`
  - Global fallback statistics → `models/per_request/global_stats.json`
- **Set all random seeds explicitly** for reproducibility (numpy, sklearn, xgboost)

Run: `python3 src/model/train_per_request.py`

**Done when:** `models/per_request/xgboost_best.json` exists alongside the four pipeline artifacts.

---

## Phase 3 — Re-run all paper experiments (~45 min)

Existing scripts (run sequentially or in parallel):

| # | Script | Produces | Replaces in paper |
|---|---|---|---|
| 3a | `train_per_request.py` (above) | LUT hierarchy + headline XGBoost MAE + bootstrap CIs | Tables 2, 3 |
| 3b | `path_decomp_ci.py` | Seen vs unseen path MAE + CIs | Path-decomposition prose + figure 3 |
| 3c | `tree_count_ablation.py` | MAE at 200 / 300 / 500 trees | Tree-count claim in §6 |
| 3d | Loss ablation (modify train script) | MAE for squared-error / Tweedie p ∈ {1.2, 1.5, 1.8} | §4 ablation paragraph |
| 3e | Feature ablation (modify train script) | MAE for regex / TF-IDF / both | §4 ablation paragraph |
| 3f | Per-resource-type evaluation | Per-type MAE | Table 4 |
| 3g | `temporal_evaluation.py` | June→Sep MAE degradation | Table 5 |
| 3h | `train_multi_target.py` | All 4 targets MAE + agg | Table 6 + figure 4 |
| 3i | `correlated_aggregation.py` | Uniform + domain-correlated agg error | Table 7 + figure 5 |
| 3j | `compute_shap.py` | SHAP attributions | §6 SHAP claim |
| 3k | `smoothed_lut.py` | Add-k LUT comparison | §4 smoothed-LUT mention |
| 3l | `advanced_analysis.py` | Calibration, distribution shift | §6 calibration claim |
| 3m | Brave LR baseline (modify train script) | sklearn Ridge MAE | §2 Brave-style baseline |
| 3n | Per-category aggregation | Already done via `src/per_category_table.py` | Table 1 (no change) |

Each result JSON gets versioned: `models/per_request/<name>_v2.json` so we don't blow away existing artifacts.

**Done when:** all 14 sub-scripts have produced results files.

---

## Phase 4 — Cross-browser empirical test (Claim B) (~30 min)

This is the new substance. Now possible because Phase 2 saved the pipeline.

`src/ua_agreement.py` (already written, do Claim A part) plus new `src/ua_model_validation.py`:

1. For each of ~200 tracker URLs:
   - Fetch with Firefox UA → ff_bytes
   - Fetch with Chrome UA → ch_bytes
   - Engineer features using saved pipeline (TF-IDF + SVD + target encodings + URL structure + request metadata)
   - Run model prediction → model_pred
2. Compute:
   - **Claim A:** ff_bytes vs ch_bytes byte-ratio distribution
   - **Claim B:** model_pred vs ff_bytes MAE
3. Report both findings.

**Done when:** `data/raw/ua_validation.csv` exists with per-URL results, summary printed.

---

## Phase 5 — Update paper with new numbers (~30-45 min)

1. Diff every numerical claim in the paper against the new results JSONs.
2. Update where they differ (likely small drift on MAE values, ablation percentages).
3. Add Claim A + Claim B findings to §3.1 and §6.
4. Re-compile, verify no `?` markers.

**Risk.** If a re-run number looks substantially different from the paper (e.g., MAE 3,466 → 3,800), investigate — could indicate a feature pipeline mismatch.

---

## Phase 6 — Page trim + anonymization + submit (~30 min)

1. Verify body fits in 6 pages (aux file).
2. Anonymization scan: `grep -i "mozilla\|james\|tim\|jhan@" paper.tex`.
3. Final compile.
4. Submit to anrw2026.hotcrp.com.

---

## What gets saved this time (not last time)

- `models/per_request/tfidf_vocab.json`
- `models/per_request/svd_components.npy`
- `models/per_request/domain_encodings.json`
- `models/per_request/global_stats.json`
- `models/per_request/xgboost_best.json` (re-trained)
- All result JSONs versioned `_v2`
- `data/raw/per_request_full.csv` (will be gitignored, but exists locally)

---

## Risk management

| Risk | Mitigation |
|---|---|
| BigQuery setup takes >1hr | If gated >1hr, fall back to Claim A only (skip rerun) |
| New numbers diverge significantly from paper | Investigate; likely pipeline mismatch. Worst case: keep paper numbers, footnote that re-run validates within X% |
| Some script crashes on fresh data | Have ~30 min buffer; debug or skip the offending experiment if non-headline |
| BigQuery cost spikes | Set `--maximum_bytes_billed=50000000000` cap; abort if exceeded |
| Fetch loop fails on some URLs | Filter to 200/200 pairs; report N successful |

---

## Order of operations (sequential, with parallel where possible)

1. **You start Phase 1 now** (BigQuery setup + queries). Tell me when CSV lands.
2. **Meanwhile I write Phase 2** (modifications to `train_per_request.py` to skip Optuna and save artifacts).
3. **You confirm CSV downloaded** → I run Phase 2.
4. I run Phase 3 sub-scripts in parallel where possible.
5. I run Phase 4 (UA test + model validation).
6. I update paper (Phase 5).
7. We do Phase 6 together.

**If anything in Phase 1 takes >45 min, abort and fall back to Claim A only path.**
