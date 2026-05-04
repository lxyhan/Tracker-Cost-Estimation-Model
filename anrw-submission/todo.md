# What's left before submission

Deadline: 4 May 2026 AoE.
Current state: 6-page compiled draft at `paper.pdf`. Format-compliant. Anonymized. Three placeholder blocks awaiting real numbers.

---

## Must do — submission blockers

These cannot ship as placeholders. Either fill or cut.

### 1. Per-category cost share (§3.3, Table~\ref{tab:per-category})
**What's needed:** real numbers for 5 rows × 3 columns (% requests, % bytes, median bytes) by tracker category (advertising, analytics, social, tag-manager, consent-provider).
**Source:** existing HTTP Archive sample. Group by `category` column from the entity table, aggregate.
**Estimated effort:** ~2 hrs (write SQL, run, format table).
**If you can't run it:** delete the table and the §3.3 paragraph that references it. Move the qualitative content into one sentence in §3.2.

### 2. Cross-list robustness (§5.2, inline placeholder)
**What's needed:** re-run model evaluation on requests classified by EasyList instead of Disconnect, report MAE shift and confirm baseline ordering preserved.
**Source:** HTTP Archive's `request_classification` table includes both classifications.
**Estimated effort:** ~3 hrs (re-filter, retrain or re-score, compute MAE).
**If you can't run it:** delete the cross-list sentence. The hyperparameter sweep alone covers the "robustness" subsection.

### 3. Hyperparameter sweep (§5.2, inline placeholder)
**What's needed:** train 9 model configurations (LR ∈ {0.03, 0.05, 0.10} × depth ∈ {6, 8, 10}), report MAE range.
**Source:** existing training pipeline, just loop over configs.
**Estimated effort:** ~2 hrs (script + 9 trains + compile results).
**If you can't run it:** delete the hyperparameter sentence. Acknowledge in §6 that "the headline configuration is reported; hyperparameter sensitivity is left to future work."

### 4. Brave-style linear regression baseline (§2, inline placeholder)
**What's needed:** train a linear regression on your existing per-request features, report its MAE.
**Source:** existing pipeline, swap XGBoost for sklearn LinearRegression.
**Estimated effort:** ~30 min.
**If you can't run it:** delete the sentence; the rest of §2 stands without it.

---

## Should do — strengthen acceptance odds materially

These are not blockers but they're high-leverage.

### 5. Bibliography cleanup
**What's needed:** remove `.bib` entries that are no longer cited (counterfactual prediction, importance weighting, domain adaptation, smyth Tweedie, jorgensen Tweedie, grinsztajn — verify each).
**Estimated effort:** ~30 min. Run `bibtex paper` after compile and check for "Warning--I didn't find a database entry" or unused entries via the `.aux` file.

### 6. Final read-through for tone
**What's needed:** scan for residual IMC/ML voice. Specifically:
- "we" claims that read as Mozilla insider (e.g., the §6 "deployment target" framing is fine but check the rest of the paper)
- defensive hedges like "while X, Y" or apologetic transitions
- repeated mentions of "Tweedie" outside §4.2 (it should be a methods detail, not a recurring theme)
**Estimated effort:** ~45 min slow read.

### 7. Limitations section tightening
**What's needed:** §8 currently has 4 paragraphs. Compress to 3 by merging server-side variation and timing metrics, or trimming temporal stability (since it's already in §5.1).
**Estimated effort:** ~20 min.

### 8. Verify all citations resolve
**What's needed:** compile, check no `?` markers in PDF for `\cite` or `\ref`, no "undefined references" in `.log`.
**Estimated effort:** 5 min.

### 9. Spot-check one specific IETF/IRTF reference
**What's needed:** §7 currently makes general claims about PEARG, MAPRG, HTTPbis charters. To strengthen, identify ONE specific recent draft, RFC, or meeting topic per RG and cite it. Even one anchors the rest.
**Source:** `datatracker.ietf.org/group/pearg/`, `datatracker.ietf.org/group/maprg/`, recent IETF meeting agendas.
**Estimated effort:** ~1 hr to find good references.
**If you can't:** the current chartered-scope language is acceptable.

---

## Nice to have — meaningful but skippable

### 10. Size/accuracy frontier (§6 or §4.2)
**What's needed:** small inline table or sentence reporting MAE at 200 / 300 / 400 / 500 trees. Currently §4.2 mentions 200 and 500 trees only.
**Estimated effort:** ~30 min if you have the trained models; ~2 hrs if you need to retrain.

### 11. Loss ablation table (currently inline)
**What's needed:** §4.3 mentions "squared-error 4,527 vs Tweedie 3,466" inline. If you have spare space, surface as a 2-row inline table for visual emphasis.
**Estimated effort:** ~10 min.
**Risk:** could push past 6 pages.

### 12. Figure caption polish
**What's needed:** every figure's caption should stand alone (a reader skimming the captions should understand the result). Spot-check Fig.~\ref{fig:cv}, Fig.~\ref{fig:domain-example}, Fig.~\ref{fig:baseline-ladder}.
**Estimated effort:** ~15 min.

### 13. Reproducibility URL placeholder
**What's needed:** §6 says "released upon publication" — if you have a private/anonymized GitHub repo or anonymous artifact link, include it. Anonymous repos are standard for double-blind submissions.
**Estimated effort:** ~30 min if creating an anon repo.

---

## Don't do — explicitly excluded

These came up in earlier discussion and were rejected for time/scope:

- ~~Cascading multiplier study~~ (different paper, requires paired crawls)
- ~~Firefox telemetry validation~~ (requires Mozilla data access you no longer have)
- ~~Per-region/vantage analysis~~ (out of scope)
- ~~Connection-level cost (TCP/TLS/DNS prevented)~~ (out of scope)

---

## Submission day checklist

On May 4 morning, before clicking submit:

- [ ] Final compile produces 6 pages technical content + reference pages
- [ ] No `[PLACEHOLDER]` strings remain in the PDF
- [ ] No `?` markers (unresolved \cite or \ref)
- [ ] Author block reads "Anonymous Author(s)" / "Anonymous Institution"
- [ ] No "Mozilla" / "James Han" / "Tim Huang" / personal email in PDF
- [ ] No "we plan / will deploy / Mozilla / Firefox Remote Settings" insider phrasing
- [ ] Conference info in header reads "ANRW '26" not "Conference '17"
- [ ] References section appears (don't accidentally suppress with `\bibliography{}` errors)
- [ ] Submission portal at `anrw2026.hotcrp.com` accepts the PDF
- [ ] Confirmation email received

---

## Realistic effort budget

If you do everything in **Must Do**: ~7 hrs. Result: clean submission, ~60% acceptance.
If you do **Must + Should**: ~10-12 hrs. Result: stronger submission, ~65-70% acceptance.
If you do **all three tiers**: ~14-16 hrs. Result: very strong submission, ~70% acceptance.

The diminishing returns curve flattens after Should. Spend the first 7 hrs on Must Do and the bib cleanup; spend any remaining time on tone read-through and the IETF reference hunt.

---

## Order of operations recommended

1. **Day 1 (May 1, remaining hours):** Write the SQL for §3.3 per-category table. Get one number on paper. Start the hyperparameter sweep (long-running; let it train overnight).
2. **Day 2 (May 2):** Hyperparameter sweep results in. Run cross-list comparison. Run Brave linear-regression baseline. Fill all four placeholder blocks. Bib cleanup.
3. **Day 3 (May 3):** Tone read-through. Limitations tightening. IETF reference hunt if time. Final compile.
4. **Day 4 (May 4 morning):** Submission-day checklist. Submit before AoE midnight.

Slack: build in at least 4 hrs of buffer for unexpected issues (figure renders, bib errors, length overflow recurring after edits).
