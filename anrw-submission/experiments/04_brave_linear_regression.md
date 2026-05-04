# Experiment 04 — Brave-style linear regression baseline

## Goal

Train a linear regression on the existing per-request feature matrix, report its MAE alongside the LUT and XGBoost numbers. Fill the Brave-LR `[PLACEHOLDER]` at `paper.tex:117`.

## Why this matters

The paper's related-work paragraph distinguishes from Brave's page-level linear regression (`brave2019savings`). Including a Brave-style linear baseline on per-request features completes the comparison: linear methods are not just at a different granularity, they're insufficient at this granularity. Closes the "did you compare against the obvious simple baseline?" hole.

Cheap (~30 min). Highest effort-to-value ratio of the four placeholders.

## Paper hole

`anrw-submission/paper.tex:114-117` (§2 Predicting blocked-resource cost):

> "For completeness we evaluate a Brave-style linear regression on our per-request features as an additional baseline; **[PLACEHOLDER]** it achieves MAE *X{,}XXX*, between the domain+type LUT and the path LUT, confirming that linear methods are insufficient for the heavy-tailed per-request setting."

## Inputs

- Existing feature pipeline: `engineer_features` at `src/model/train_per_request.py:91`
- Existing train/test split (seed 42, 70/15/15)
- `sklearn.linear_model.LinearRegression` (or `Ridge` with small α to handle near-collinear TF-IDF dimensions cleanly)

## Method

1. Load the same `X_train, y_train, X_test, y_test` used for the headline XGBoost model.
2. Apply log1p to `y_train` (consistent with the heavy-tailed target). Optionally do not — Brave's paper used raw bandwidth as the target. Try both and report the better one to be charitable to the baseline.
3. Fit `LinearRegression()` (or `Ridge(alpha=1.0)`).
4. Predict on test, invert log1p if applied (`np.expm1(pred).clip(min=0)`).
5. Compute MAE via the existing `evaluate(y_true, y_pred, label="LinReg")` at `src/model/train_per_request.py:167`.

## Expected output

Replace `paper.tex:114-117` placeholder line with a clean sentence (and add a row in `Table~\ref{tab:main-results}` if space permits, otherwise inline):

```
For completeness we evaluate a Brave-style linear regression on our per-request
features (\texttt{sklearn.linear\_model.LinearRegression}, log-transformed target):
MAE X{,}XXX, between the domain+type LUT (6{,}597) and the path LUT (3{,}797).
Linear methods cannot capture the multiplicative interactions between domain
target encodings, URL embeddings, and resource type that the gradient-boosted
model exploits.
```

Expected MAE range: 5,000–7,000. If LR somehow comes in below the path LUT, that's a finding — investigate and rewrite accordingly.

## Effort

~30 min:
- 5 min: copy `train_per_request.py` skeleton, swap XGBoost for LinearRegression
- 5 min: fit + predict
- 5 min: format sentence
- 15 min: buffer

## Risks / blockers

- **Numerical issues from raw-target LR.** The 8.6 MB max value will cause leverage problems. Use log1p target, or `HuberRegressor` for robustness if vanilla LR explodes.
- **TF-IDF dimensions sparse-but-dense after SVD.** SVD output is dense float, fine for sklearn. No special handling needed.

## Fallback if blocked

Cut the sentence at `paper.tex:114-117`. The §2 paragraph stands without it: the differentiation from Brave is the granularity (per-request vs. per-page) and the unobservable-response framing, not the baseline comparison.

## Done when

- [ ] `models/per_request/linreg_baseline.json` (or pickle) exists with MAE
- [ ] `paper.tex:114-117` placeholder removed, real sentence in place
- [ ] (Optional) Row added to Table 2 main results
- [ ] PDF compiles
