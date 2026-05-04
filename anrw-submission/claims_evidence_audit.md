# Claims↔Evidence Audit

Every numerical claim in `paper.tex` must trace to a specific experimental artifact. This doc is the audit trail.

Two-model strategy (from final_version_05_03.md): canonical "deployed" model is **April 2026**; **June 2024** model is used only for the temporal degradation curve (where you need an old model to measure decay).

---

## §1 Introduction

| Claim | Evidence | Source |
|---|---|---|
| ETP blocks billions of requests per day | Public Mozilla telemetry context | Citation only (no measurement) |
| 258B tracking pixel from bat.bing.com vs 170KB JS SDK | Illustrative example | Verified against `data/raw/firefox_crawl/` HARs |

---

## §3 The Tracker Cost Landscape

| Claim | Evidence | Source |
|---|---|---|
| 3,490,824 requests across 3,723 tracker domains (June 2024) | June 2024 1% sample | `sql/05_per_request_full.sql` → `data/raw/05_per_request_full/per_request_full.csv` |
| 2,655,452 requests across 6,285 tracker domains (April 2026) | April 2026 1% sample | `sql/17_recent_apr2026.sql` → `data/raw/17_recent_apr2026/per_request_apr2026.csv` |
| Within-domain CV median 0.94, p90 3.0 | Per-domain CV computed on 1% sample | `src/within_domain_cv.py` (TBD: or compute from training data) |
| Tag manager: 6.3% req / 40.6% bytes; Advertising: 66.5% / 17.8% | Per-category aggregation | `src/per_category_table.py` → `data/raw/per_category.csv` |
| 99.2% request, 98.6% byte coverage | Per-category script output | Same as above |
| LUT hierarchy MAE values (13,661 / 7,878 / 6,578 / 3,795) | Computed from April 2026 train/test split | `src/rerun_paper_numbers.py` → `models/per_request/rerun_paper_numbers.json` |
| 75% of unique test paths unseen | Rerun path-decomp output | Same |
| 14.9% Sept paths in June training | Old paper claim — needs re-verification | TBD: compute from June↔Sept overlap |
| Path LUT extrapolates to ~23M entries at full pop | 227K from 1% sample × 100 = 22.7M | Arithmetic from rerun |

**Cross-browser empirical (§3.1 paragraph (iii)):**

| Claim | Evidence | Source |
|---|---|---|
| 46 tracker URLs tested | Live UA test | `src/ua_agreement.py` → `data/raw/ua_agreement.csv` |
| Median byte ratio 1.000 | UA agreement summary | Same |
| 97.8% within 5% byte agreement | Same | Same |
| Single outlier: Google reCAPTCHA at 0.63 | Same | Same |

---

## §4 Estimating the Unobservable Response

| Claim | Evidence | Source |
|---|---|---|
| Model MAE 4,318 (April 2026) | Training run | `models/per_request/multi_target_results.json` |
| Model MAE 4,274 (April 2026, 6-type) — earlier | Pre-11-type run | superseded |
| **Need new headline MAE bootstrap CI from rerun_paper_numbers.py on April 2026 model** | TODO | TBD |
| Spearman ρ 0.9324 | Multi-target results | Same |
| D+T LUT MAE 6,802 | Same | Same |
| 36.5% improvement vs LUT | Same | Same |
| 80 features (was) → 85 features (now) | Feature column count from feature_columns.json | `models/per_request/feature_columns.json` |
| Per-resource-type breakdown | Multi-target results | Same |

**Path decomposition** (UPDATED — April 2026 numbers needed):

| Claim | Old (paper) | Rerun (June 2024 model) | NEW (April 2026 model) |
|---|---|---|---|
| pct seen | 91.6% | 91.6% | TBD |
| seen LUT MAE | 1,448 | 1,473 | TBD |
| seen model MAE | 1,346 | 1,529 | TBD (likely > LUT) |
| Honesty: model is now statistically TIED with path LUT on seen paths in the rerun. Need to reframe (cf. user's earlier prompt to drop "beats memorization" framing). |

---

## §5 Robustness

| Claim | Evidence | Source |
|---|---|---|
| Temporal degradation at 1/3/6/12 months | June 2024 model evaluated on Jul/Sep/Dec 2024/Jun 2025 holdouts | `src/temporal_curve.py` → `models/per_request/temporal_curve.json` (TBD: running now) |
| 32.8% advantage retained at 3 months | Old paper number from temporal study | Will be replaced by `temporal_curve.json` numbers |
| Multi-target results (4 targets) | Old paper Table 8 | TBD: re-run with April 2026 model? Or keep old for now? |
| Aggregation simulation (uniform + correlated) | Existing analysis on test split | `models/per_request/advanced_analysis_results.json` |

---

## §6 Deployment

| Claim | Evidence | Source |
|---|---|---|
| 500 KB ONNX model size | Asserted; needs measurement | TBD: Convert model to ONNX, measure size |
| 50 µs median, 93 µs p99 inference | Measured on June 2024 model (429 trees) | `src/onnx_benchmark.py` output `/tmp/...` |
| **Need to re-run benchmark on April 2026 model** (different tree count) | TODO | TBD |
| Resident memory ~5 MB | Asserted (vocabulary + ensemble) | TBD: verify |
| Tree-count elbow at 500 | Old paper claim | Should re-verify on April 2026 model |
| SHAP \|φ\|=3.16 for domain_type_median | Old SHAP analysis on different model | `src/compute_shap.py` — TBD: re-run on April 2026 model |

**NEW: Claim B in-page Firefox validation (§6.x to add):**

| Claim | Evidence | Source |
|---|---|---|
| 35-page Firefox crawl with mobile emulation | Playwright Firefox + Moto G4 mobile UA + 360x640 viewport | `src/firefox_crawl.py` → `data/raw/firefox_crawl/har_*.json`, `types_*.json` |
| 6,172 tracker requests across 499 domains | After category filter (Disconnect's 4 trained categories + manual tag-managers) | `src/claim_b_har_analysis.py` → `data/raw/claim_b_in_page_validation.csv` |
| Per-request: model MAE 8,367 vs LUT 7,423 | Same | Same |
| Aggregation N=200 uniform: model 23.4% vs LUT 31.3% | `src/claim_b_aggregation.py` | Output above |
| Aggregation domain-correlated: model 38.2% vs LUT 47.5% | Same | Same |
| 75% seen-path / 25% unseen-path split | Path coverage decomposition | One-off analysis |
| Seen-path MAE 5,073 (within 17% of test MAE 4,274) | Same | Same |

---

## §7 IETF/IRTF Implications

Mostly framing claims; numbers cited from §3 per-category and §6 deployment. No new evidence needed.

---

## §8 Conclusion

| Claim | Evidence |
|---|---|
| Numbers cited from §3-§6 | Already audited above |
| Future work: telemetry replay, longer-horizon temporal, cross-list, cross-vendor | Acknowledged honestly |

---

## Open TODOs

1. **Re-run rerun_paper_numbers.py on April 2026 model** (currently it points at April CSV but uses canonical model artifacts which ARE April 2026 — should give correct numbers but verify)
2. **Re-run ONNX benchmark on April 2026 model** (current 50µs was measured on June 2024 model with 429 trees; April model has different tree count)
3. **Measure ONNX file size after conversion** (asserted 500KB; need to verify)
4. **Wait for temporal_curve.py to finish** (running now)
5. **Update path decomposition prose** to reflect rerun finding (model statistically tied with path LUT on seen paths)
6. **Recompute within-domain CV on April 2026 data** (was 0.94/3.0 on old data)
7. **Re-run SHAP on April 2026 model** if we want to keep that claim

## What gets cut for length

If we run out of pages, in priority order to cut:
- SHAP paragraph (model internals)
- Calibration paragraph (model internals)
- Tree-count ablation detail (1 sentence is enough)
- Smoothed LUT mention
