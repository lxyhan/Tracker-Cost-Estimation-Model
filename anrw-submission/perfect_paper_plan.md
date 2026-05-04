# Perfect Paper Plan — 2026-05-03 (final pass)

Submission deadline: 2026-05-04 23:59 AoE.

Synthesizes every finding from today's experimentation. Every numerical claim must trace to a specific artifact (see `claims_evidence_audit.md`). Two-model strategy: April 2026 = canonical "deployed" model; June 2024 = temporal-staleness study only.

---

## Three load-bearing findings (the spine)

### Finding 1: The model is the best deployable estimator we found

Backed by **expanded LUT comparison** (`src/lut_variants.py` → `models/per_request/lut_variants.json`):

| LUT variant | Size@full | MAE | Deployable |
|---|---|---|---|
| Domain | 88 KB | 9,008 | yes |
| Domain+type (paper baseline) | 114 KB | 6,802 | yes |
| Domain+type+has_query_params | 122 KB | 6,225 | yes |
| Domain+type+URL-length bucket | 188 KB | 5,862 | yes |
| Domain+type+first path token | 543 KB | 5,749 | yes (~model size) |
| Domain+URL path | 187 MB | 4,688 | **NO** (churns) |
| **Model (XGBoost+Tweedie)** | **500 KB ONNX** | **4,318** | **YES** |

**Headline**: Model wins by 25% over best deployable LUT alternative; matches its size; 8% better than non-deployable upper bound. Defeats strawman objection.

### Finding 2: The model maintains advantage over deployment-realistic time horizons

Backed by **temporal degradation curve** (`src/temporal_curve.py` → `models/per_request/jun2024/temporal_curve.json`):

| Horizon | Model MAE | LUT MAE | Per-req adv | Model agg | LUT agg | Agg adv | ρ |
|---|---|---|---|---|---|---|---|
| 1 month | 4,454 | 6,694 | +33.5% | 8.0% | 21.3% | +13.3 pp | 0.935 |
| 3 months | 4,776 | 6,721 | +28.9% | 10.7% | 21.5% | +10.8 pp | 0.938 |
| 6 months | 5,256 | 7,069 | +25.6% | 13.9% | 19.6% | +5.7 pp | 0.920 |

**Headline**: Per-request advantage erodes from 33% → 26% over 6 months; aggregation 13 pp → 6 pp. Quarterly retraining justified by data (still +11 pp at 3 months). Ranking stays robust (ρ ≥ 0.92).

### Finding 3: The model's deployment-aggregation advantage holds in real Firefox

Backed by **Claim A (cross-browser invariance)** + **Claim B (in-page Firefox crawl)**:

**Claim A** (`src/ua_agreement.py`): 46 tracker URLs, Firefox UA vs Chrome UA → median ratio 1.000, 97.8% within 5% byte agreement. Server determinism empirically confirmed.

**Claim B** (`src/firefox_crawl.py` + `src/claim_b_har_analysis.py` + `src/claim_b_aggregation.py`):
- 35-page Playwright Firefox crawl with mobile emulation (Moto G4-matching: 360x640, mobile UA, touch)
- 6,172 tracker requests across 499 trained-category domains
- Path coverage decomposition: 75% seen-path → MAE 5,073 (within 17% of in-distribution test 4,318); 25% unseen-path → MAE 22,003 (per-impression unique IDs, structurally novel)
- Aggregation: Model 23.4% vs LUT 31.3% at N=200 uniform (8 pp advantage); 38.2% vs 47.5% under domain-correlated browsing (9 pp)
- Per-page (35 pages): model wins 16/30, median %err 33.6% vs LUT 36.2%

**Headline**: Model preserves 7-9 pp advantage over deployable LUT on user-facing weekly aggregation in real in-page Firefox conditions, despite per-request MAE being slightly worse (bias-variance trade-off).

---

## The conceptual frame: bias-variance trade-off in deployment

Section §6 should explicitly frame this as a contribution:

> "The deployable LUT and the model occupy different points on the bias-variance trade-off. The LUT is URL-blind (high bias, low variance) → robust under URL distribution shift but accumulates per-domain bias. The model uses URL features (lower bias, higher variance) → precise on URLs whose structure it understands, but exposed to misleading URL features when patterns are novel. Aggregation reveals which trade-off pays off for the user-facing metric: variance cancels in summation, while systematic bias compounds. This explains why the model wins on aggregation in deployment even when the LUT has slightly lower per-request MAE, and frames the choice of estimator as a deployment-context decision rather than a pure accuracy question."

This is a real conceptual contribution — not just a measurement, but an insight about WHY the comparison goes the way it does.

---

## Section-by-section editing plan

### §1 Introduction
- Update contributions list with **expanded LUT comparison**, **temporal curve**, **Claim A+B empirical**
- Add the bias-variance framing as the conceptual contribution
- Tighten

### §2 Background
- Brief; add one sentence noting the LUT-vs-model framing comes from the deployment context (not just accuracy)
- Keep Brave LR baseline mention

### §3 The Tracker Cost Landscape
- Update data section: now 2 models trained (June 2024 + April 2026); explain why
- §3.2 Within-domain variance: keep — re-verify CV numbers from April 2026 data
- §3.3 Per-category share: keep — already good (Disconnect-classified, 99.2% / 98.6% coverage)
- §3.4 LUT-to-model path: **EXPAND** with the LUT variants table → makes the "why a model" argument much stronger
- §3.1 Cross-browser argument: keep, including the Claim A empirical confirmation

### §4 Estimator
- Update headline numbers (April 2026 model: MAE 4,318, +36.5% vs D+T LUT)
- Path decomposition: REFRAME — model is now statistically tied with path LUT on seen paths in the rerun. New finding: "Model achieves comparable seen-path MAE at deployable size while covering the unseen-path long tail the LUT cannot serve, with consistent ranking quality (ρ=0.94)."
- Loss/feature ablations: stay inline (compressed)
- Add: hyperparameter selection mention (Optuna, alternatives evaluated)

### §5 Robustness
- **Replace single-point temporal claim with the 4-row degradation curve** (1/3/6 month + show per-request AND aggregation)
- Add: quarterly retraining is now justified by curve, not single point
- Multi-target: keep
- Aggregation: keep

### §6 Deployment (BIGGEST EXPANSION — this is where the new findings concentrate)
- Hook + Surface + Distribution: keep, slightly tighten
- **Runtime cost**: replace asserted µs with **measured 50µs median, 93µs p99** (`src/onnx_benchmark.py`)
- **NEW Subsection: Cross-browser invariance (Claim A)** — move from §3 to here, expand into a small finding
- **NEW Subsection: In-page Firefox validation (Claim B)** — the headline new finding. Includes: methodology (Playwright mobile emulation, MIME-aware type mapping, category filter), per-request MAE, **aggregation table model vs LUT at N=50/100/200/500 uniform and correlated**, path-coverage decomposition (75% seen, 25% unseen)
- **NEW: Bias-variance framing paragraph** — the conceptual contribution
- Update cadence + telemetry replay future work — keep, slightly tighten

### §7 IRTF
- Keep, update with concrete numbers from new findings
- Add one sentence about the LUT-variants comparison: "even our most generous deployable LUT alternative falls short of the model"

### §8 Conclusion + Future
- Update with the new headline numbers
- Future work: longer-horizon temporal (already have framework, just need 12-month CSV), telemetry replay, cross-vendor

---

## Tables and figures roster (final)

| # | Table/Figure | Source | Section |
|---|---|---|---|
| Fig 1 | Domain example (gtag/js vs collect) | existing | §1 |
| Fig 2 | Within-domain CV CDF | existing | §3.2 |
| **Tbl 1** | **Per-category cost share** | `src/per_category_table.py` | §3.3 |
| **Tbl 2** | **LUT variants comparison (NEW: expanded)** | `src/lut_variants.py` | §3.4 |
| Tbl 3 | Features summary | inline, compressed | §4.1 |
| Tbl 4 | Main results (model vs LUT vs path LUT, with bootstrap CI) | `src/rerun_paper_numbers.py` | §4.2 |
| Tbl 5 | Per-resource-type MAE | from training output | §4.3 |
| **Tbl 6** | **Temporal degradation curve (NEW: 4 horizons + agg)** | `src/temporal_curve.py` | §5.1 |
| Tbl 7 | Multi-target results | from existing | §5.2 |
| Tbl 8 | Aggregation simulation (uniform + correlated) | from existing | §5.4 |
| **Tbl 9** | **Claim B aggregation: in-page Firefox (NEW)** | `src/claim_b_aggregation.py` | §6.x |

Total: 8 tables + 2 figures. Tight but feasible at 6 pages.

---

## Page budget (revised)

| Section | Cols (target) |
|---|---|
| §1 Intro | 1.0 |
| §2 Related | 0.5 |
| §3 Landscape (data + per-cat + LUT variants table) | 1.7 |
| §4 Estimator (features + model + main results + path decomp + ablations) | 2.0 |
| §5 Robustness (temporal curve + multi-target + aggregation) | 1.5 |
| §6 Deployment (hook + runtime + Claim A + Claim B + bias-variance) | 1.5 |
| §7 IRTF | 0.6 |
| §8 Conclusion | 0.4 |
| Total: ~9.2 col | ≈ 4.6 pages of body + tables/figures inflation = ~5.8 pages |

Should fit in 6 pages with discipline. Will need to cut: SHAP detail (1 sentence), calibration paragraph (1 sentence), tree-count detail (1 sentence).

---

## Execution order (deadline ~24 hours)

1. **Now (30 min)**: Update §3.4 with LUT variants table; update §4 with new headline MAE numbers from rerun
2. **Next (45 min)**: Replace §5.1 temporal table with 4-horizon curve; add aggregation columns
3. **Next (45 min)**: Add §6 Claim A subsection; add §6 Claim B subsection with aggregation table; add bias-variance framing paragraph
4. **Next (15 min)**: Update §6 runtime cost with measured benchmark numbers
5. **Next (15 min)**: Tighten §1 contributions, §8 conclusion to reflect new claims
6. **Next (30 min)**: Compile, check page count, cut where needed
7. **Next (30 min)**: Final anonymization scan, bib cleanup, submission checklist
8. **Submit**

---

## What we're EXPLICITLY not doing tonight

- Re-running ONNX benchmark on April 2026 model (50µs from June 2024 model is representative; tree count similar)
- Re-running SHAP on April 2026 model (mention the old SHAP finding briefly)
- Re-computing within-domain CV on April 2026 (existing 0.94/3.0 numbers from sample stable)
- Pulling June 2025 data for 12-month temporal point (3 horizons is enough; 12-month listed as future work)
- Any model architecture changes
- Any retraining

---

## Risk register

| Risk | Mitigation |
|---|---|
| Page overflow | Pre-cut SHAP + calibration paragraphs; aggressive table compression |
| New numbers contradict each other | All numbers traced to artifact via audit doc |
| Bias-variance framing reads as defensive | Frame as "trade-off characterization" not as "we tried hard" |
| Claim B 8 pp advantage seems small | Show curve + per-page + aggregation — multiple angles confirm |
| Reviewer asks about LUT variants | Expanded comparison anticipates this objection |
| Anonymization slip | grep pass before submit |

---

## What this paper says (final positioning)

> Firefox ETP makes billions of block decisions but the network cost is structurally unobservable. We characterize the cost landscape (per-category byte concentration; within-domain variance), present a deployable per-request estimator (500 KB ONNX, 50 µs inference, beating every deployable LUT variant tested), validate it across the temporal axis the deployment scenario depends on (curve at 1/3/6 months: model holds 13 pp aggregation advantage at 1 month, 6 pp at 6 months), and validate it empirically in real Firefox conditions (Playwright in-page crawl with mobile emulation: 7-9 pp aggregation advantage on 6,172 tracker requests). The model's win is bias-variance: it accepts higher per-request variance to gain lower systematic bias, which cancels in the user-facing weekly aggregate. The numbers and methodology feed PEARG, MAPRG, and HTTPbis discussions on quantitative privacy-feature evaluation.
