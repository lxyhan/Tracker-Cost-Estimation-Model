# Plan: 500-page parallel Firefox crawl

Replace the curated 35-page in-page crawl (current §6.3 / Fig 5b) with a
Tranco-sampled 500-page crawl. The result either confirms or revises the
"7--9 pp aggregation advantage" headline. Pre-registration is the key
discipline; the rest is engineering.

---

## 0. Pre-register the sampling rule before running anything

This is the single most important step. Write the methodology paragraph
into `paper.tex` §6.3 *first*, commit it, then run the crawl. If the
crawl produces inconvenient numbers, the temptation to retroactively
adjust the rule is real and reviewers can smell it. Pre-registering in
the draft makes silent adjustment impossible.

The locked rule:

> *Tranco top-1000 list (list ID `<TRANCO_LIST_ID>`, generated
> `<TRANCO_DATE>`), filtered to the first 500 reachable publisher
> pages. Each page crawled once with headless Firefox via Playwright,
> Moto G4 mobile emulation matching HTTP Archive (360x640 viewport,
> mobile UA, touch enabled), 30-second page timeout, 5-second
> post-load hold, fresh browser context per page.*

Capture the Tranco list ID and date in the paragraph the moment you
download the list — these uniquely identify the sample. Tranco re-ranks
nightly; without these, the sample isn't reproducible.

Tranco URL: <https://tranco-list.eu/>

---

## 1. Crawl architecture

**Source files to modify:**
- `src/firefox_crawl.py` (current script, 158 lines, sequential, 35
  hand-curated pages) → fork to `src/firefox_crawl_500.py` so the
  35-page version stays runnable for sanity-check (§4 below).

**Parallelism**: 5 Playwright workers, each with its own browser
process. Aggressive enough to finish in ~1 hour, bounded enough to
avoid OS-level resource contention or rate-limiting from CDNs that
front many trackers.

**Per-page protocol** (must match the 35-page crawl exactly so
results are comparable):
- Fresh `BrowserContext` per page (no cookie carryover across pages)
- 30-second page timeout
- 5-second post-load hold for late-firing trackers
- HAR capture with `_transferSize` field (matches HTTP Archive's
  `_bytesIn`)
- Mobile emulation: viewport 360x640, mobile UA, touch enabled

**Output structure**: `data/raw/firefox_crawl_500/har_NNN_<host>.json`
plus `_crawl_summary.json` with per-page success/failure metadata.

---

## 2. Failure logging (non-negotiable for honest reporting)

Every page that does not complete the protocol must log a failure
mode. Categories:
- `timeout` — page never fired `load` event within 30s
- `navigation_error` — DNS, TLS, or HTTP error before any content loaded
- `consent_wall` — page redirected to a consent UI and never resolved
  (heuristic: load completes but page contains < 5 third-party requests)
- `headless_detected` — page detected headless and served different
  content (heuristic: very low tracker count vs typical for the domain)
- `other` — anything else, with the raw exception message

The paper must report exclusion counts. A paper that says "of 500
sampled domains, X failed to load and Y returned no tracker requests,
leaving Z in the analysis" reads as honest; one that silently reports
"500 pages" when the target was 500 reads as suspicious to anyone who
checks closely.

---

## 3. Operational steps

```bash
# Step A: pre-register methodology paragraph in §6.3 of paper.tex,
# commit. Capture Tranco list ID + date.

# Step B: download Tranco list
curl -o data/raw/tranco_top1000_<DATE>.csv \
  "https://tranco-list.eu/download/<LIST_ID>/1000"

# Step C: build the URL list (top 500 reachable publishers)
python3 src/build_tranco_top500.py \
  --tranco data/raw/tranco_top1000_<DATE>.csv \
  --out data/raw/tranco_top500_pages.txt

# Step D: parallel crawl
python3 src/firefox_crawl_500.py \
  --urls data/raw/tranco_top500_pages.txt \
  --workers 5 \
  --out data/raw/firefox_crawl_500/

# Step E: pipeline (compute aggregation %err with model and LUT)
python3 src/claim_b_aggregation.py \
  --crawl-dir data/raw/firefox_crawl_500/ \
  --out models/per_request/claim_b_500page.json
```

---

## 4. Sanity check before trusting new numbers

Before reading the 500-page result, run the analysis pipeline against
the *35-page* archive and confirm it reproduces the current Fig 5b
numbers within rounding (7--9 pp aggregation advantage at every
browsing scale). If the 35-page rerun does not match, there is a
pipeline bug; find and fix it before touching the 500-page result.

This is a 30-minute check that prevents a category of disaster where
a pipeline bug masquerades as a measurement shift.

```bash
python3 src/claim_b_aggregation.py \
  --crawl-dir data/raw/firefox_crawl/ \
  --out models/per_request/claim_b_35page_rerun.json

# Compare claim_b_35page_rerun.json against the values currently in
# Fig 5b (7--9 pp advantage at N=50/100/200/500 in both uniform and
# domain-correlated). If they diverge by more than rounding, stop.
```

---

## 5. Decision branches based on the 500-page result

The current paper claims a +7--9 pp aggregation advantage. The 35-page
crawl is small-N; the true value at 500 pages could be anywhere
roughly in [+4, +11] pp. Three pre-written contingencies:

### Branch A: result lands in roughly +6 to +10 pp
**Headline holds.** Update Fig 5b numbers, update prose ranges, update
abstract if the range shifts. Ship.

### Branch B: result lands meaningfully smaller (+3 to +5 pp)
**Reframe, don't hide.** Report the new number, acknowledge that the
35-page result overstated the effect, and adjust the paper's
contribution claim:
- Model still beats deployable LUT
- Advantage is smaller than initially estimated
- Methodology and open artifact are the contribution

This is *not* a disaster. Reviewers respect honesty about effect-size
shifts under increased N; they punish papers that hide them.

### Branch C: result lands meaningfully larger (+10 to +13 pp)
**Don't celebrate prematurely.** A larger effect at larger N sometimes
indicates a sampling artifact (e.g., Tranco top-500 over-represents
heavy-tracker publishers).

Spot-check by computing the result on stratified subsamples (top 100,
middle 200, bottom 200 by Tranco rank) and confirming the advantage
is stable across strata.

If stable: ship the bigger number with confidence.
If not: report it with a stratification caveat and the smaller
"average across strata" number.

```bash
python3 src/claim_b_stratified.py \
  --crawl-dir data/raw/firefox_crawl_500/ \
  --strata 0:100,100:300,300:500 \
  --out models/per_request/claim_b_500page_stratified.json
```

---

## 6. Reconciliation editing pass

The new numbers replace the existing Fig 5b numbers, the existing
35-page text gets rewritten to reference 500, and the abstract claim
gets updated to whatever the 500-page result shows.

Search the whole paper for these strings — every instance needs to
be reconciled:

- `35-page` / `35 page` / `35` (in §6.3 prose)
- `7--9` and `7-9` (the percentage-point range)
- `7--9\,pp` (with LaTeX thinspace, in abstract and conclusion)
- `6{,}172 tracker requests` (the per-request count from the 35-page crawl)
- `499 domains` (the per-domain count from the 35-page crawl)

Locations to inspect:
- Abstract (line ~51)
- Contributions (line ~74)
- §6.3 deployment-validation paragraph
- Fig:robustness caption
- §8 conclusion

Roughly a 30-minute editing pass at the end. Search with `grep -n`,
not by reading.

---

## 7. Archival (rebuttal-ready)

Keep the 35-page crawl data and pipeline output archived after the
swap:

```bash
mv data/raw/firefox_crawl/         data/raw/firefox_crawl_35page_v1/
mv models/per_request/claim_b_35page_rerun.json \
   models/per_request/claim_b_35page_v1.json
```

If a reviewer asks during rebuttal "did the 35-page version produce
the same conclusion," the answer needs to be "yes, here's the
comparison" rather than "we replaced it and didn't keep records."

---

## 8. Engineering work to do before the crawl runs

Concrete tasks, in dependency order:

1. **`src/build_tranco_top500.py`** (does not exist yet) — read Tranco
   CSV, filter to https-reachable HEAD-200 hosts, cap at 500, write
   one URL per line. Should be robust to redirects (follow up to 3) and
   rate-limit politely (200ms between checks).

2. **`src/firefox_crawl_500.py`** (fork of `firefox_crawl.py`) —
   accept `--urls` arg, parallelize via `multiprocessing.Pool` of 5
   workers each running a Playwright browser. Per-worker isolation:
   each worker process owns its browser, contexts are fresh per page
   within the worker. Log every failure mode to
   `_crawl_summary.json` with structured fields (`url`, `outcome`,
   `error`, `n_requests`, `bytes_total`).

3. **`src/claim_b_stratified.py`** (does not exist yet) — variant of
   `src/claim_b_aggregation.py` that bins requests by source-page
   Tranco rank stratum and reports aggregation %err per stratum. Only
   needed if Branch C is triggered.

Estimated implementation time: ~3 hours for the three scripts, ~1 hour
for the crawl itself, ~30 min for sanity check and pipeline reruns,
~30 min for reconciliation editing. About a half-day end-to-end if
nothing goes wrong, longer if Branch B or C triggers.

---

## What this plan does *not* do

- Does not change the model, training pipeline, or LUT baseline.
- Does not change the aggregation methodology (uniform vs
  domain-correlated sampling, N values, bootstrap CI procedure).
- Does not introduce new evaluation metrics.

The crawl is the *only* thing changing. Everything downstream is the
same code path applied to a larger, sampled, exclusion-logged
dataset. That is the source of the credibility gain.
