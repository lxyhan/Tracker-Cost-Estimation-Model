# ANRW '26 Paper Outline

**Thesis:** ETP blocks billions of tracker requests per day but the network cost is structurally unobservable. We characterize the cost landscape and build the per-request estimator needed to do so at URL-level resolution.

**Format:** 6 pages, ACM sigconf, double-blind. Deadline 2026-05-04 AoE.

---

## Topics that make up the paper

| § | Topic | What it claims | Status |
|---|---|---|---|
| 1 | The gap | ETP blocks billions of requests; response is structurally unobservable; IRTF cares | **Have** (current draft §1) |
| 2 | Related work | Brave page-level LR; WhoTracks.Me; Ghostery; ETP itself | **Have** (current draft §2) |
| 3a | Within-domain variance | CV spans 3 OOMs across 3,723 domains | **Have** (current draft §3.2 + Fig 7) |
| 3b | Per-category cost shares | Tag-manager + advertising dominate bytes despite minority of requests | **MISSING** — Experiment 01 |
| 3c | Per-resource-type breakdown | Scripts/CSS dominate bytes; beacons negligible | **Have** (in 12-page paper, not ported to ANRW) |
| 3d | How we got to a model | Walk through the LUT hierarchy at increasing granularity: domain alone leaves CV 0.94; +type leaves CV 0.14 with a tail; +path matches well but 75% of unique test paths are unseen and the URL space churns. Conclusion: we need something that generalizes across URL *structure*, not memorizes exact keys. That points to a model. | **Have** (current draft §3.4) — table stays, surrounding prose needs rewrite |
| 4a | The estimator (features + model) | XGBoost + Tweedie + TF-IDF, 80 features | **Have** (current draft §4) |
| 4b | Headline result | The model achieves the URL-level resolution §3 identified as needed: lower error on the paths the path LUT can match, plus coverage of the paths it cannot. Non-overlapping bootstrap CIs. | **Have** (current draft Table 2) |
| 4c | What URL structure carries | On the 91.6% of test rows where exact-path memorization is possible, the model's prediction is closer to truth than the empirical median. URL structure carries information beyond key identity; the model captures it. | **Have** (current draft Table 3) |
| 5a | Temporal robustness | June→Sep, 30% degradation, 32.8% advantage retained | **Have** (current draft Table 4) |
| 5b | Cross-list robustness | Headline holds under EasyList classification | **MISSING** — Experiment 02 |
| 5c | Hyperparameter robustness | Headline holds across 3×3 LR × depth grid | **MISSING** — Experiment 03 |
| 6 | Multi-target measurement | Transfer/download URL-predictable; TTFB/load network-dominated; aggregation favors model on all 4 | **Have** (in 12-page paper, not ported to ANRW) |
| 7 | Aggregation | Weekly 6.0% (uniform) / 12.9% (correlated); model advantage widens under correlation | **Have** (current draft §5.3) |
| 8 | Deployment | 500KB ONNX, microsecond inference, quarterly retraining | **Have** (current draft §6) |
| 9 | IRTF implications | Specific drafts in PEARG, MAPRG, HTTPbis | **Partial** — section exists but generic; needs specific refs (research, not data work) |
| 10 | Limitations + conclusion | | **Have** (current draft §8) |

Optional related-work polish:
| ext | Brave LR baseline | LR insufficient on per-request features (MAE 9,651, worse than D+T LUT) | **Have** — existing Ridge result in `models/per_request/per_request_results.json`; surface in §2 |

---

## Summary

**Have (already in current draft or in 12-page paper, just need porting):** 11 of 14 topics.

**Missing (need new data work):** 3 topics — all 3 are in `experiments/`:
- 01: Per-category cost shares
- 02: Cross-list (EasyList) robustness
- 03: Hyperparameter sweep

**Polish only (no data):** §9 IRTF implications needs specific drafts cited.

**Already done but forgotten:** Brave LR baseline (Ridge MAE 9,651 in existing results JSON).

---

## Gating dependency

Experiments 02 and 03 need `data/raw/per_request_full.csv` (NOT on disk). Regenerate via `sql/05_per_request_full.sql` in BigQuery.

Experiment 01 runs entirely server-side in BigQuery — does NOT need the local CSV.
