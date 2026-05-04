# Experiment status

Submission: 2026-05-04 23:59 AoE.

| # | Experiment | Status | Result |
|---|---|---|---|
| 01 | Per-category cost-share table | **DONE** | Tag manager 6.3% req / 40.6% bytes; Advertising 66.5% req / 17.8% bytes; full table at `paper.tex:tab:per-category` |
| 04 | Brave-style linear regression | **DONE (Option A)** | Ridge MAE 9,651 already in `models/per_request/per_request_results.json`; needs surfacing in §2 prose |
| ~~02~~ | ~~Cross-list (EasyList)~~ | **CUT** | Defensive padding; same model + same URLs across lists makes the test essentially tautological. Replaced with 1-sentence acknowledgment in §10. |
| ~~03~~ | ~~Hyperparameter sweep~~ | **CUT** | Optuna already ran 75–150-trial automated search in `train_per_request.py:209`; a 3×3 grid on top is pseudo-rigor. Replaced with 1-sentence acknowledgment in §10. |

Per-category table source: `src/per_category_table.py`, output `data/raw/per_category.csv`.

No data work remaining. All further edits are prose surgery.
