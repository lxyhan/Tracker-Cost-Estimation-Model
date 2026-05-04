# Final Version Plan — 2026-05-03

Submission: ANRW '26, deadline 2026-05-04 23:59 AoE.
Current draft: 7-page PDF (body extends to page 7; references on 7).

---

## Order of operations

User-decided sequence:
1. Empirical cross-browser UA test (substantive)
2. ONNX inference latency microbenchmark (substantive)
3. Verify the Brave-LR baseline claim
4. Page trim (formal compliance)
5. Final anonymization scan

Rationale: substantive risk reduction first; formal/cosmetic last. The substantive items address the two supervisor-flagged "most likely to sink the paper" objections (cross-browser validity, asserted-not-measured deployment).

---

## Task 1 — Empirical cross-browser UA test

**Goal.** Quantify the "User-Agent content negotiation affects a minority of requests by small fractions" claim from §3.1, replacing assertion with measurement.

**Method.**
1. Sample ~200--500 tracker URLs from common tracker domains (Google Tag Manager, Google Analytics, DoubleClick, Facebook, etc.). Either (a) pull URL patterns from existing `request_features_agg.csv` domains plus known endpoint paths, or (b) construct a list of common tracker URLs from the top-traffic domains we have.
2. For each URL, fetch twice via Python `requests`:
   - Once with `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0`
   - Once with `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`
3. Record HTTP status + `len(response.content)` for each.
4. Filter to URL pairs where both fetches returned 200 OK.
5. Compute per-URL:
   - Byte ratio: `min(firefox_bytes, chrome_bytes) / max(firefox_bytes, chrome_bytes)` (1.0 = identical)
   - Absolute byte diff
6. Aggregate:
   - Median byte ratio
   - Fraction of URL pairs within 5% / 10% / 50% byte agreement
   - Fraction with substantial divergence (ratio < 0.5)
   - p90 byte difference
7. Report a 1--2 sentence finding in §3.1, e.g., "an empirical check on N tracker URLs sampled from the test set found median byte ratio X.XX with Y% of pairs within 10% byte agreement, supporting the bounded-residual-variation claim."

**Caveats to acknowledge in prose:**
- Single-vantage fetch (no geo variation tested)
- Single-moment fetch (no time-of-day / A/B variation)
- Uncookied (most tracker beacons/scripts don't depend on cookies for content)
- Bot-detection may serve generic responses to both UAs

**Effort.** 30--60 min: 15 min URL list, 15 min fetch loop + run, 15 min aggregate + paper edit.

**Output.**
- `data/raw/ua_agreement.csv` (per-URL results)
- 1--2 sentence finding inserted into §3.1 third argument bullet
- Optional small inline table if results are striking

**Done when.** Real number replaces "affects a minority by small fractions" assertion in §3.1(iii).

---

## Task 2 — ONNX inference latency microbenchmark

**Goal.** Replace "low double-digit microseconds per request on commodity x86" assertion in §6 with a measured number.

**Method.**
1. Convert `models/per_request/xgboost_best.json` to ONNX format via `onnxmltools` or `xgboost.Booster.save_model` + `onnxconverter-common`. (Or: if there's already an ONNX export somewhere, use it.)
2. Generate a synthetic feature batch (1000 rows × 80 features) matching the model's input schema. Use random uniform / normal values; calibrated values not needed for latency timing.
3. Use `onnxruntime` Python API to load the model and run inference:
   - Warm-up: 100 single-request inferences
   - Measure: 10,000 single-request inferences, record per-call latency
4. Compute median, p99, mean latency.
5. Run on this machine (commodity x86, single-threaded, CPU-bound mode).

**Effort.** 30--45 min: 15 min ONNX export, 10 min benchmark script, 10 min run + format result.

**Output.**
- Concrete numbers in §6 "Runtime cost" paragraph: e.g., "median 18 µs, p99 47 µs (10,000 runs, single-threaded onnxruntime on x86)".

**Done when.** Real benchmark numbers in §6, replacing the "low double-digit microseconds" assertion.

---

## Task 3 — Verify the Brave-LR baseline claim

**Goal.** Confirm the §2 sentence "a Brave-style ridge regression... achieves MAE 9,651, worse than the domain+type LUT" accurately reflects what was actually run.

**What to check:**
1. The existing Ridge result in `models/per_request/per_request_results.json`:
   - α = 1.0 (sklearn default)
   - Trained on the same 80-feature matrix as XGBoost
   - On raw target (no log transform)
2. Brave's actual paper [brave2019savings] used log-transformed target for bandwidth ($R^2{=}0.68$). To be charitable to the baseline, we should ideally re-run with log1p target.
3. If we can't re-run (no `per_request_full.csv` on disk), we should at minimum:
   - Note that our Ridge result uses raw target while Brave used log target
   - State this honestly in the prose

**Decision branch:**
- **(A)** If we can recover the per-request training data (regenerate from BigQuery or find a cached copy), re-run with `Ridge(alpha=1.0)` on `np.log1p(transfer_bytes)` target, invert via `np.expm1(pred).clip(min=0)`. Report new MAE.
- **(B)** If we can't, soften the claim to "a Brave-style ridge regression on raw transfer-bytes targets achieves MAE 9,651" so it's accurate even if not maximally charitable. Add a sentence noting that log-target framing might close part of the gap but not the headline.

**Effort.** 10--30 min depending on branch.

**Output.** Verified or revised §2 Brave-LR sentence.

---

## Task 4 — Page trim

**Goal.** Conclusion currently on page 7 per aux file; need it on page 6 to comply with "6 pages technical content" ANRW limit.

**Approach.** Rather than blanket compression, identify the specific paragraph(s) crossing the page 6 boundary and target those.

**Compression candidates ranked by cost:**
- §6 deployment opener — could be 1 sentence instead of 2
- §3 per-category clarification paragraph — could merge with the per-category prose
- §3 within-domain variance paragraph — already 2 sentences, could be 1
- §7 IRTF paragraphs — already inline-bold; could merge MAPRG + HTTPbis
- Drop one figure if needed (path-decomp or aggregation CDF — both have equivalent table data)
- Merge §5.4 aggregation methodology paragraph into the table caption

**Effort.** 15--30 min iterative (compile after each cut, re-check page boundaries).

**Done when.** Aux file shows `\newlabel{sec:conclusion}{...{8}{6}...}` (page 6 not 7).

---

## Task 5 — Final anonymization scan

**Goal.** Catch any leftover Mozilla / author / internal references that would identify authors.

**Checks:**
1. `grep -i "mozilla\|firefox\|james\|tim huang\|jhan@\|@mozilla" paper.tex` — review each hit for author-revealing context.
2. Search compiled PDF text for the same patterns: `pdftotext paper.pdf - | grep -i "..."`.
3. Verify author block reads "Anonymous Author(s)" / "Anonymous Institution".
4. Verify no acknowledgments section, no email addresses.
5. Verify bib entries don't include identifying info (e.g., URLs to internal Mozilla resources).
6. Check `paper.aux`, `paper.log` aren't included in submission (they shouldn't be — only `paper.pdf` is uploaded).
7. Reaffirm artifact link line says "withheld for double-blind compliance".

**Notes:**
- "Firefox" is OK throughout — it's a public product, not author-revealing.
- "Mozilla" might be OK in carefully-scoped uses (e.g., "Firefox's Remote Settings"), but flag any instance and judge case-by-case.
- "ETP" is OK — public Firefox feature.

**Effort.** 10--15 min.

**Done when.** All grep results either OK or rewritten.

---

## Submission checklist (after all tasks)

- [ ] PDF compiles cleanly with no `?` markers (unresolved \cite or \ref)
- [ ] No `[PLACEHOLDER]` strings in PDF
- [ ] Body content fits in 6 pages (verify via aux file)
- [ ] Author block reads "Anonymous Author(s)"
- [ ] No "Mozilla" / personal names / personal emails in PDF
- [ ] No artifact URL pointing to mozilla.org / github.com/mozilla
- [ ] Conference info: ANRW '26, July 20, Vienna
- [ ] References render (not accidentally suppressed)
- [ ] Submission portal: anrw2026.hotcrp.com
- [ ] Confirmation email received

---

## What we're explicitly NOT doing tonight

- Larger §3 reorg (supervisor's "polish point")
- New strong learned baseline beyond Ridge (gradient-boosted with squared-error already in our loss ablation)
- Repository scrub for `anonymous.4open.science` artifact (deferred to post-acceptance camera-ready)
- Mirror repo to non-Mozilla GitHub account (also deferred)
- §3.4 reorganization
- Additional figures

These are valuable but not blockers; the four substantive items above plus page trim + anonymization are the path-of-victory edits.
