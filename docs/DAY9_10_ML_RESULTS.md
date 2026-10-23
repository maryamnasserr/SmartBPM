# Days 9–10: explainable predictive analytics

This document records the frozen Day 9?10 stage. The current six-model dashboard and advanced XAI are documented in [Days 11?12](DAY11_12_ADVANCED_ML_XAI.md); original v1 results and artifacts remain preserved.

Implemented and verified 20–21 October 2026 (Africa/Cairo). SmartBPM now has a functional **Predictive Analytics** validation workbench with saved sklearn models, real validation-case risks, mathematically checked explanations and interactive Plotly diagnostics. It is not a live organizational prediction service. No recommendation engine, simulation, LLM, agent or Day 11 feature was implemented.

## Preserved research design and locked test

No discrepancy requiring a target/split change was found. The original log has 10,500 cases; the frozen unresolved ML dataset has 9,536 cases. Training has 5,783 cases (1,320 positive / 4,463 negative), validation 1,752 (496 positive / 1,256 negative), and 2,001 test cases remain locked. Training prevalence is 0.22825523084904029; validation prevalence is 0.2831050228310502.

Prediction is immediately after the second recorded event in canonical UTC timestamp/source-row order. The positive class is **total observed elapsed case duration strictly greater than 11.105428240740741 days**. Equality is negative. This outcome threshold remains the p75 of 5,951 mature Event-2 training outcomes before known-positive removal; it is not an official SLA and is never refitted by the new modeling code. It is distinct from the probability threshold used to classify model risks.

The existing 60/20/20 chronological boundaries and endpoint-purging rules remain unchanged: validation starts 2018-06-27T09:27:50 UTC, test starts 2018-10-12T13:06:56 UTC. Eligibility still reconciles as 134 singletons + 333 known positives + 497 additional overlap exclusions + 9,536 unresolved cases = 10,500. The 520 original overlap cases include 23 known positives. See the Days 7–8 methodology for the original reference cohort and selection limitations.

The modeling loader compares case/split/prediction-time metadata against the frozen audit, including test membership. It reads modeling records only with train/validation predicates. Test identifiers/splits/times and whole-file hashes are allowed for integrity checks; **test features/outcomes are not transformed, predicted, scored or used for model selection**. Earlier preparation tests still check historical dataset consistency, but no test predictive metric is computed. The model output files contain validation cases only. Case IDs, split and label are never predictors.

## Preprocessing and exact model configurations

Only six approved source predictors enter the modeling API: `first_activity`, `second_activity`, `prefix_elapsed_hours`, `utc_month`, `utc_weekday`, `utc_hour`. Resources/roles, final case attributes, future activity/count/variant/outcome information, identifiers, absolute timestamps and source provenance are excluded.

All learned preprocessing is fitted inside sklearn Pipeline/ColumnTransformer on training rows only:

- Elapsed hours: training-median imputation, fixed `log1p`, then training StandardScaler. All-missing synthetic training columns are retained with sklearn's empty-column fallback. Negative/infinite elapsed values are rejected.
- First/second activity and calendar values: constant missing token `__MISSING__`, then training-only full one-hot encoding. Unknown categories produce all-zero indicators; no holdout vocabulary is fitted. Real prepared activity/timestamp fields are nonmissing. Calendar month/weekday/hour are nominal categories rather than imposing an ordinal linear effect. Values outside valid calendar ranges are rejected.
- No class weighting, oversampling, feature selection, random cross-validation or probability recalibration. Calendar nominal encoding/log elapsed are modeling transformations of the same approved predictors, not a new prediction problem.

This follows sklearn's guidance on fitting preprocessing only within training pipelines; see [common pitfalls and leakage prevention](https://scikit-learn.org/stable/common_pitfalls.html).

| Family | Fixed configuration / limited comparison |
|---|---|
| Prevalence baseline | DummyClassifier(strategy=`prior`), training positive fraction; features do not change its risk |
| Elapsed baseline | LogisticRegression using only transformed elapsed hours; C=1, lbfgs, max_iter=2000, tol=1e-8 |
| Logistic regression | Same solver/settings, full approved feature set; compare C=0.1 and C=1; select **C=0.1** |
| Constrained tree | Gini, min_samples_leaf=100; compare max_depth=3 and 4; select **depth=4** |

Random seed is **42**. Six candidate fits total: two baselines, two logistic settings, two tree depths. Convergence warnings fail the run rather than silently publishing unconverged models. Candidate AP values: prevalence .283105; elapsed .377694; logistic C=.1 **.465132**, C=1 .454234; tree depth=3 .356474, depth=4 **.356588**.

## Selection and decision-threshold policy

The rule was fixed before the first run: rank by validation **average precision**, with Brier as a within-family tie-break. For preferred-family near-ties within .005 AP of the best, favor simpler models in the order prevalence, elapsed, logistic, tree. The selected family is logistic regression. It has the highest AP, ROC-AUC and lowest Brier among the four retained models.

For every model, choose a probability decision threshold maximizing validation F1 over the same fixed grid `.01, .02, …, .99`. Ties choose the value closest to .5, then the higher value. A case is predicted positive when `p >= decision_threshold`. This is an exploratory operating point, not a validated organizational cost/benefit policy. The UI slider explores validation tradeoffs without retraining or saving changes. Comparison-table classification metrics retain the saved per-model thresholds; fixed .50 metrics are provided separately.

## Actual validation comparison

All metrics below use the same 1,752 validation cases. ROC-AUC, average precision and Brier use probabilities; classification metrics use each saved decision threshold. Average precision summarizes the PR curve using recall increments, not trapezoidal interpolation; see [sklearn's average precision definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).

| Model | Probability threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | Average precision | Brier ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Training prevalence | .22 | .283105 | .283105 | 1.000000 | .441281 | .500000 | .283105 | .205965 |
| Elapsed-time baseline | .21 | .283105 | .283105 | 1.000000 | .441281 | .554053 | .377694 | .200709 |
| **Logistic regression** | **.20** | **.594749** | **.379775** | **.681452** | **.487734** | **.672844** | **.465132** | **.189335** |
| Constrained tree | .28 | .526256 | .342453 | .731855 | .466581 | .605747 | .356588 | .194993 |

Confusion matrices use rows `[observed negative, observed positive]` and columns `[predicted negative, predicted positive]`:

| Model | TN | FP | FN | TP |
|---|---:|---:|---:|---:|
| Prevalence | 0 | 1,256 | 0 | 496 |
| Elapsed | 0 | 1,256 | 0 | 496 |
| Logistic | 704 | 552 | 158 | 338 |
| Tree | 559 | 697 | 133 | 363 |

F1 tuning makes both baselines predict every validation case positive. This is a real consequence of that tuning objective, not fabricated performance. At a fixed .50 threshold, prevalence instead predicts everyone negative: accuracy .716895, precision/recall/F1 0. The elapsed baseline has accuracy .729452 / precision .775 / recall .0625 / F1 .115672. Logistic has accuracy .726027 / precision .673913 / recall .0625 / F1 .114391. Tree has accuracy .728311 / precision .884615 / recall .046371 / F1 .088123. Accuracy alone therefore obscures the smaller positive class.

Logistic AP exceeds the strongest baseline (elapsed) by **0.08743735362599447** absolute, about 8.74 percentage points. This exceeds the predeclared .01 descriptive margin and supports additional validation ranking value from the richer model. It is not a statistical significance claim or proof of operational usefulness. At threshold .20, 552 false positives accompany 338 true positives, so review burden and limited precision matter. The tree does not beat the elapsed baseline on AP, despite adding feature complexity.

Both family selection and threshold tuning use this same validation set. All validation results are consequently selected/exploratory and may be optimistic. No test evaluation, training+validation refit or extra post-result search was performed.

## Probability quality

Reliability diagrams use ten fixed-width probability bins, omitting empty bins and reporting every occupied bin's sample size. Brier is mean squared probability error; lower is better, but it reflects discrimination and outcome uncertainty as well as calibration. See [sklearn probability calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).

Logistic Brier is **.18933478892781347**, better than elapsed **.20070876247938527** and prevalence **.2059650685593505**. However, mean predicted validation risk is only **.22773187702205114**, against observed prevalence **.2831050228310502**. It generally underestimates risk in populated low/mid bins:

| Probability bin | Cases | Mean predicted risk | Observed positive share |
|---|---:|---:|---:|
| 0–.1 | 168 | .083727 | .113095 |
| .1–.2 | 694 | .150470 | .200288 |
| .2–.3 | 486 | .254052 | .304527 |
| .3–.4 | 273 | .328874 | .399267 |
| .4–.5 | 85 | .455268 | .588235 |
| .5–.6 | 22 | .543713 | .681818 |
| .6–.7 | 15 | .661759 | .533333 |
| .7–.8 | 8 | .729185 | .875000 |
| .8–.9 | 1 | .822230 | 1.000000 |

High-risk bins are sparse and uncertain. Better Brier does not establish fully calibrated individual risk. No calibrator was fitted to these validation outcomes; doing so and reporting the same outcomes as independent calibration performance would be misleading.

## Global and individual explanations

Saved logistic coefficients refer to the transformed design matrix. Selected associations include:

| Transformed feature | Coefficient | exp(coefficient) |
|---|---:|---:|
| UTC month September | −.581891 | .558841 |
| Event 2: rejected by supervisor | +.538977 | 1.714253 |
| Event 2: final approved by supervisor | −.516606 | .596542 |
| UTC weekday Monday | −.508623 | .601323 |
| UTC month November | −.479152 | .619309 |
| UTC month February | +.414547 | 1.513685 |
| Event 2: approved by administration | −.398546 | .671295 |
| Standardized log1p elapsed hours | +.314631 | 1.369754 |

Full one-hot coefficients are relative to the encoded origin; contrasts within the same category group are more meaningful than treating a category coefficient as an intervention effect. The elapsed coefficient corresponds to one training standard deviation of log1p hours, not one raw hour. Calendar associations can reflect seasonality, cohort composition and observation boundaries; they do not identify causes or guarantee future stability.

The logistic case explanation computes every `transformed_value × coefficient`, adds the intercept and applies the logistic function. Tests verify that this reproduces the model risk numerically. Contributions are log-odds terms, not percentage-point changes. The intercept is the encoded-origin intercept, not the training positive fraction. Unknown categories receive zero one-hot contributions.

For a tree case, the UI lists the exact transformed decision path and the reached leaf's training sample size. Its positive share must equal predict_proba. Global tree importance is training impurity reduction, not a signed effect, validation importance or causal evidence. The prevalence explanation explicitly states that every case receives the same training prior; no feature explanation is invented.

### Real validation example: declaration 110775

- Event 1: Declaration SUBMITTED by EMPLOYEE, **2018-07-13T08:08:03 UTC**.
- Event 2: Declaration APPROVED by ADMINISTRATION, **2018-07-13T08:08:06 UTC**.
- Prefix elapsed: **3 seconds**, .0008333333333 hours. Calendar: July, Friday (weekday 4), UTC hour 8.
- Selected logistic risk: **.2514116137835614 (25.1%)**.
- Decision threshold .20 → predicted **long-running**.
- Actual historical target **0** → **false positive**. This deliberately shows a real mistake rather than cherry-picking a success.
- Intercept **−.9167973036526247**, summed contributions approximately **−.1743004861697987**, total log-odds **−1.0910977898224234**; sigmoid equals the saved risk.

Only Event-2 predictors are supplied to the model. The outcome is displayed for retrospective validation, never passed into the predictive matrix. The example contains no live/new organizational-data claim.

## Dashboard and manual walkthrough

The new page follows the existing light/teal SmartBPM layout. Overview cards show training/validation size, preferred model and selected validation AP. Model and threshold controls sit above four tabs. Existing sidebar filters do not refit models or change the frozen validation population.

1. Launch the app with the command below and choose **Predictive Analytics** in Explore.
2. Confirm 5,783 training / 1,752 validation cases, preferred **Logistic**, AP **.465**, and a locked test holdout of 2,001. The duration cutoff remains 11.105428240740741 days; the separate decision slider defaults to .20 for logistic.
3. In **Model comparison**, switch the metric between average precision, ROC-AUC, Brier and classification metrics. Read the four-model table. Expand the baseline help for fixed .50 comparisons. Higher is better except Brier.
4. In **Validation evaluation**, inspect the confusion matrix (704 TN, 552 FP, 158 FN, 338 TP at .20), class distribution, ROC, PR and reliability charts. Hover reliability points for sample counts. Mean predicted risk 22.8% versus observed 28.3% is a calibration warning, not a claim of perfect probabilities.
5. Move the probability slider. Confusion counts, predicted classes and case correctness change; probabilities, ROC/PR curves, model parameters and saved comparison metrics do not. Slider changes are exploratory and not saved.
6. In **Case prediction explorer**, select `declaration 110775`. Confirm the activities, three-second prefix, timestamp and 25.1% risk. At .20 it is an incorrect positive classification; at .50 the same probability gives a negative class. Expand the exact calculation.
7. Use **Inspect model** to compare tree, elapsed baseline and prevalence on that same case. Tree shows its decision path and leaf; prevalence explains its constant risk. Select another real validation case to check the details update.
8. In **Research interpretation**, read the preferred-model rationale, limitations and coefficient/importance table. The model selector controls which family's associations are displayed; it does not change the saved preferred model.
9. Resize the window or use a narrow mobile viewport. Cards stack; chart/table areas remain within the page. Wide tables scroll internally, tabs scroll horizontally and long activity names wrap.
10. Navigate back to Overview, Process Mining, Performance Investigation or ML Preparation. Their existing calculations remain available. Preparation/investigation text now refers to the trained-model page while distinguishing its own historical statistics from predictions.

## Commands and file inventory

Use the existing virtual environment. Install the pinned dependency additions if this is a fresh checkout:

```powershell
Set-Location 'C:\Users\Maryam Nasser\Desktop\SmartBPM'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/run_day9_10.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8505 --browser.gatherUsageStats false
```

Open **http://localhost:8505**. The execution script trains the fixed small comparison and exports validation artifacts; opening/navigating the app does not train. Keep the Streamlit terminal open; Ctrl+C stops it. If prepared data is absent, reproduce Days 7–8 first with `scripts/prepare_ml_dataset.py`.

New reusable modules:

- `src/smartbpm/ml_training.py`: strict feature schema, frozen development loader, sklearn pipelines, limited comparison, prediction, exact explanations and artifact persistence/verification.
- `src/smartbpm/ml_evaluation.py`: metrics, fixed-grid threshold selection and ROC/PR/reliability diagnostics.
- `src/smartbpm/ui_predictive.py`: cached, read-only model/validation workbench; no fitting/test evaluation.
- `scripts/run_day9_10.py`, `scripts/verify_ml_artifacts.py`, `scripts/verify_predictive_browser.py`, `tests/test_ml_training.py`.

Saved model folder `outputs/models/day9_10/`:

- `models.joblib`: four selected pipelines (4,431 bytes in this run).
- `manifest.json`: artifact version **1.0**, sklearn/Python/NumPy/Pandas versions, provenance, dataset/model/prediction hashes and development case membership. Seed/configurations are recorded in `validation_report.json`.
- `validation_predictions.parquet`: 1,752 cases and four probability columns plus identifier/timestamp/label; no test probabilities (55,617 bytes).
- `validation_report.json`: comparison, candidate configurations, thresholds, curves, calibration and limitations.
- `logistic_explanation.csv`, `tree_explanation.csv`, `elapsed_explanation.csv`, `prevalence_explanation.csv`.

Reports under `outputs/reports/`: `day9_10_model_comparison.csv`, `day9_10_validation_results.json`, `day9_10_calibration.json`, `day9_10_example_case.json`, `day9_10_runtime.json`, and final verification evidence. Saved local model files use joblib/pickle and must be trusted project-generated files; the app has no model-upload feature. Integrity/version checks and exact probability/metric read-back run before the cached UI bundle is used. The model folder remains ignored by the existing `.gitignore`; regenerate it from the script when moving the project.

Updated files include `app.py`, `requirements.txt`, the preparation/investigation status wording, historical browser assertions, README, the existing beginner guide and development progress. Existing raw/cleaned/ML-ready/audit Parquets are unchanged. New dependencies are pinned: scikit-learn **1.9.1**, joblib **1.6.0**, threadpoolctl **3.7.0**, cloudpickle **3.1.2**; other pinned packages were retained.

## Verification and remaining limits

Baseline before code edits: **116 passed**, one optional PM4Py accelerator warning, **119.42 s**. Focused ML tests: **18 passed** after correcting synthetic missing-value construction and normalizing exported prediction indices. They cover known-answer metrics, thresholds, calibration occupancy, prevalence math, elapsed-only independence, train-only preprocessing, missing/unknown categories, strict schemas/order, forbidden inputs, partition guards, exact case explanations, serialized prediction equality, repeatability, corrupt-artifact rejection, guarded real-data loading and Streamlit integration.

Final full regression after current-status wording and regression updates: **134 passed, zero failed, one existing optional PM4Py warning, 235.41 seconds**. `pip check` found no broken requirements. No convergence warning occurred. AppTest's known bare-mode logging warning is distinct from rendered app exceptions. The earlier full run also passed 134 tests in 247.46 seconds.

An additional independent audit (`scripts/verify_ml_artifacts.py`) recomputed actual validation AP by grouped precision/recall increments, ROC-AUC by Mann–Whitney average ranks, confusion/precision/recall/F1 by counts, and Brier by squared errors. All matched saved results within 1e-12. It independently checked threshold-grid optima, train-only scaler statistics/vocabularies and development case membership. Evidence: `outputs/reports/day9_10_independent_verification.json`. No test prediction was generated.

Actual headless Edge verification passed: all four model choices, metric control, probability-threshold slider, real validation-case selection, five evaluation charts, exact confusion cells, interpretation tab and all eight existing pages. The four predictive tabs each fit a 390px document/viewport in simulated mobile. **Zero rendered exceptions and zero console errors** in the clean run. Cold predictive navigation measured **15.041 seconds** in this environment. Desktop/mobile screenshots were directly inspected; a clipped model heading and raw technical contribution labels were improved before final verification. Screenshots/results are under `outputs/reports/browser_checks/day9_10/` (`verification.json`, overview/evaluation/case/interpretation PNGs). They are verification evidence; the dashboard itself uses interactive charts, not PNGs.

Initial browser attempts needed model-change/slider-readiness correction. Buffered connection-refused errors from a deliberate server restart were outside the subsequent clean-run log scope; the final run cleared historical log buffers before navigation and asserted no new console errors. Intermediate failure captures are retained separately under `intermediate_attempts/`. The final dedicated browser/profile was closed/removed; the Streamlit application remains available at http://localhost:8505. No cross-browser or physical-device coverage is claimed.

The pipeline ran twice, produced the same validation results and reproduced predictions exactly after serialization. First execution measured **11.759 s**; a concurrent-tests rerun measured **21.222 s**, including verification/export but excluding interpreter imports. All four protected dataset hashes stayed unchanged. Local timings are workload-dependent.

This is a defensible first historical-validation module, not production certification. Important limits remain: censored observed outcomes, unverified completion/ingestion time, source-order ties, landmark/known-positive/purging population selection, historical cohort drift, selected-validation optimism, sparse high-risk bins, underprediction and moderate precision. There is no inference upload/live-data integration, intervention effect or causal conclusion. The holdout remains locked for a later explicitly authorized final evaluation. Days 9–10 stop here; Days 11–12 require user approval and must respect these limitations.
