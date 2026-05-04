# ANRW '26 Submission Planning

Target: regular paper, 6 pages technical + unlimited refs.
Deadline: 4 May 2026 AoE.
Source: 12-page IMC-framed draft at `paper.tex`.

---

## Path of victory: the strongest possible ANRW paper

The win-condition target. Designed first; cut/reframe work is reverse-engineered from this.

### Title

**"Quantifying What Enhanced Tracking Protection Saves: A Measurement Study of Firefox's Deployed Privacy Intervention"**

### Thesis

Firefox ETP is a privacy intervention deployed to hundreds of millions of users that makes billions of blocking decisions per day, but the IETF/IRTF community has no quantitative answer to "how much network traffic does it actually prevent?" We close that gap with a measurement study and a deployable estimator.

### Contributions (ANRW-shaped, five)

1. **Measurement of the modern tracker ecosystem.** Within-domain transfer-size variance across 3,723 tracker domains (CV 0.94 median, 3.0 p90 — three orders of magnitude). Per-category cost characterization (advertising, analytics, social, tag-manager, consent-provider) showing how blocked bandwidth distributes across the tracker landscape. The "we measured X in the wild" contribution.

2. **A deployable estimator for the structurally-unobservable cost.** XGBoost model with full engineering constraints surfaced: ONNX artifact ~500KB, browser-side inference, Remote Settings delivery, retraining cadence. Headline result with bootstrap CIs that don't overlap with the strongest non-model baseline (path LUT). The "real system shipped to real users" contribution.

3. **A counterintuitive measurement finding.** Model beats exact-path memorization on the 91.6% of test rows where the path LUT has an exact training match (1,346 vs 1,448 MAE, non-overlapping CIs). Memorable result that reviewers cite.

4. **Temporal and ecosystem-robustness characterization.** Train June, test September; what degrades, by how much, why (URL path churn at 14.9% unique-path retention). Cross-list robustness check (Disconnect vs EasyList classification). Hyperparameter sensitivity sweep. The "operationally honest" contribution operators value.

5. **Implications for IETF/IRTF privacy measurement work.** Concrete numbers feeding into PEARG (privacy enhancements), MAPRG (protocol measurement at scale), and HTTPbis (third-party content) discussions. The "engages with our community" contribution that closes the fit gap.

### Cheap empirical additions (no new crawls, ~10-12 hrs)

These strengthen contributions 1-4 using only existing HTTP Archive data already in the pipeline:

- **Hyperparameter sensitivity sweep.** LR × max-depth grid (~9 configs) reported as a single table. Closes the "no automated search" reviewer hole. ~2 hrs.
- **Cross-list robustness.** Re-run evaluation under EasyList classification instead of Disconnect to show the result isn't list-specific. HTTP Archive has both. ~3 hrs.
- **Per-category cost table.** Median + total bandwidth share by tracker category. Pure measurement, no new model. Adds an ANRW-flavored measurement table. ~2 hrs.
- **Bootstrap CIs on the temporal-holdout numbers.** Strengthens §5. ~1 hr.
- **Per-category prediction quality breakdown.** Show the model's per-category MAE and aggregation accuracy. Surfaces which categories drive the headline number. ~2 hrs.

### Structure

1. **Intro** — ETP is deployed, cost question is open, why it matters for the IETF/IRTF community
2. **Background** — ETP, Disconnect list, HTTP Archive, related IETF/IRTF activity
3. **Measurement: the tracker cost landscape** — within-domain variance, distributional structure, per-category share, what makes prediction hard
4. **Estimating the unobservable** — model + LUT hierarchy + headline result + path-decomposition surprise
5. **Robustness** — temporal holdout, cross-list check, hyperparameter sensitivity, correlated-browsing aggregation
6. **Deployment** — artifact size, integration path, retraining cadence
7. **IETF/IRTF implications** — what this measurement means for active standards conversations (NEW)
8. **Limitations and future work**
9. **Conclusion**

### Reviewer-eyes test

- **Operator on PC:** "Browser vendor measured what their privacy feature does, shipped a model, told us how to evaluate it, gave us numbers we can cite." → strong accept
- **Academic measurement reviewer:** "Credible HTTP Archive measurement, bootstrap-validated improvement, honest temporal holdout, cross-list robustness, deployment artifact." → solid accept
- **IRTF chair:** "Engages with our community's questions, provides citable numbers." → fit confirmed
- **Skeptical reviewer 2:** "Hyperparameter sweep done, cross-list checked, CIs reported, gap to truth honestly bounded." → no easy ding

### Realistic ceiling

~65-70% acceptance probability if all of this lands cleanly. Above base rate (55-60%). Above what the paper as-written hits. The remaining ~30% is noise from reviewer assignment, fit subjectivity, and the inherent variance of a peer-reviewed workshop.

---

## Audience reminders

IETF/IRTF protocol engineers and network operators. Reward measurement of deployed systems, operational realism, deployment artifacts, engagement with active standards work, reproducibility. Do not reward novel ML methods, theory, or actuarial-science framing.

---

## What stays, what goes

### Keep (load-bearing)

1. **Within-domain transfer-size measurement.** CV 0.94 median, 3.0 p90, across 3,723 tracker domains. Most ANRW-citable finding. Keep numbers + CV figure.
2. **Deployment story.** Firefox ETP integration, ONNX ~500KB, Remote Settings, Disconnect grounding. Operator/vendor signal. Keep §7 intact, expand by one paragraph.
3. **HTTP Archive grounding.** 3.5M requests, June 2024 mobile, hash-based reproducible sample. Compress hard.
4. **Headline LUT-ladder result with bootstrap CIs.** Non-overlapping CIs vs path LUT. Keep table, compress prose.
5. **Path-decomposition surprise.** Model beats exact-path memorization on 91.6% of seen paths. Memorable counterintuitive finding.
6. **Temporal holdout.** June→September, 30% degradation but 32.8% advantage retained. Operationally crucial.
7. **Aggregation accuracy + correlated browsing.** Within 10% 68.5% of weeks; correlated browsing widens the model's advantage. Table stays, prose compresses.

### Compress (1-2 sentences each)

8. **Loss-function ablation.** Reframe as "off-the-shelf XGBoost defaults are wrong for zero-inflated web data." ~1/2 column.
9. **Feature ablation.** TF-IDF subsumes regex. Few lines.

### Cut entirely

- §5.7 Calibration — self-admitted weakness, not load-bearing.
- §5.6 Multi-target timing — mixed message; deployment is transfer-size only anyway.
- §6.1 Domain-level negative finding — side-quest from per-request thesis.
- Tweedie-parameter sensitivity sub-ablation — known robust.
- Smoothed LUT (add-k) comparison — methodological completeness only.
- Per-resource-type table → one sentence.
- SHAP vs gain feature importance — reviewer-bait, not core.
- Covariate-shift / counterfactual / domain-adaptation related-work paragraph — IMC voice.
- "Why no neural baselines" → 1 line.

---

## Reframing decisions

### Abstract (5 sentences, measurement-forward)

1. Firefox ETP blocks billions of requests but reports zero performance information to users.
2. Quantifying the cost is a measurement problem with a structural gap: the response is never received.
3. We measure within-domain transfer-size variance across 3,723 tracker domains using HTTP Archive (CV spans three orders of magnitude).
4. We train a deployable XGBoost model that estimates per-request cost from pre-response features alone, with bootstrap-validated improvement over the path-level lookup table.
5. The model is being integrated into Firefox; we report deployment artifact size, temporal stability over a 3-month holdout, and weekly aggregation accuracy.

### Intro

Lead with deployment story and measurement gap. Tweedie loss demoted from contribution to methods detail. Four-bullet contribution list as above (measurement / deployment / temporal / standards-relevance).

### New: §8 IETF/IRTF implications

~1 column. Hooks:
- **PEARG (Privacy Enhancements RG)** — quantitative privacy-feature evaluation methodology
- **MAPRG (Measurement and Analysis for Protocols RG)** — web-traffic measurement at scale
- **HTTPbis WG** — third-party content cost as input to protocol-level discussions
- **Privacy Sandbox attribution reporting** — independent measurement complements vendor self-reports
- **Operator concerns** — CDN traffic shaping, ISP load implications of widespread tracker blocking

### Reframe specifics

- Tweedie loss → engineering choice, not contribution. One sentence in §4.
- "Counterfactual" framing → cut. Replace with "structurally unobservable response."
- Actuarial-science citations → cut.
- Title leads with measurement and deployment, not prediction.

---

## Page budget (6 pages two-column)

- Title + abstract + keywords: 0.4 col
- §1 Introduction (with IETF connection): 1.5 col
- §2 Background + related work: 0.8 col
- §3 Measurement: tracker cost landscape: 1.5 col
- §4 Estimating the unobservable (methods + headline): 2.5 col
- §5 Temporal stability: 1.0 col
- §6 Aggregation: 1.0 col
- §7 Deployment: 1.0 col
- §8 IETF/IRTF implications: 1.0 col
- §9 Limitations: 0.5 col
- §10 Conclusion: 0.4 col
- **Total: ~11.6 columns = 5.8 pages**

Tight but feasible. ~0.2 page slack.

---

## Anonymization

- Author block (`paper.tex:25-40`): redact James Han + Tim Huang + Mozilla affiliations.
- "Mozilla" → "a major browser vendor" where it would reveal authorship.
- "Firefox" stays — public product, not author-revealing.
- Acknowledgments empty.

---

## Hard checkpoints

- **End of day 1 (May 1):** Reframed abstract + intro + cut list executed. Length ~9 pages.
- **End of day 2 (May 2):** Fully reframed body. New §8 drafted. Length ~6.5 pages.
- **End of day 3 (May 3):** Polish, anonymize, final cut to ≤6 pages, compile, verify figures.
- **May 4 morning:** Submit.

---

## Risks

- **Length.** 12 → 6 is real surgery. Risk of overshooting at 7 pages on day 3.
- **Reframing depth.** IMC framing is baked into prose, not just abstract. Multiple paragraphs need rewriting.
- **§8 IETF implications.** New section; needs research on which IRTF RGs to cite. Allow ~2 hours.
- **Hyperparameter weakness.** Reviewer 2 may flag "no automated search." Mitigation: cut sentence or run quick LR/depth sweep.
- **Capacity.** Past week was hard. ~16-22 hours over 3 days assumes capacity has rebuilt.

---

## Fallback

If end-of-day-2 length >7.5 pages, branch a 2-page short-paper version. Submit whichever lands cleaner.
