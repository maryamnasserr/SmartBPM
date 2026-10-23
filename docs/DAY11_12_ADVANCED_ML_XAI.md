# Days 11–12: advanced predictive monitoring and explainable AI

Implemented and verified on 2026-10-21. Artifact version **2.0**. This is a historical research prototype, not an independently evaluated deployment. No LLM, recommendation engine, simulation or agent was implemented.

## Research objective and preserved population

Predict, immediately after the second recorded event, whether total observed declaration duration is **strictly greater than 11.105428240740741 days**. This inherited training-derived research cutoff is not an official SLA. Equality is negative. The probability decision threshold is a separate quantity.

The unchanged source contains 10,500 cases and 56,437 events across 17 activities. The frozen unresolved Event-2 population is 9,536: training **5,783**, validation **1,752**, locked test **2,001**. Training has 1,320 positives (22.83%); validation has 496 positives (28.31%). Original eligibility, singleton/already-known-positive exclusions, chronological boundaries and endpoint overlap purging are preserved. Exclusions mean findings do not generalize to all original declarations. Observed last events need not establish business completion; censoring and historical availability uncertainty remain.

Only `first_activity`, `second_activity`, `prefix_elapsed_hours`, `utc_month`, `utc_weekday`, and `utc_hour` enter a pipeline. Calendar fields are UTC at Event 2. Identifiers are display/provenance metadata. Outcomes are evaluation-only. Future events, final case attributes and resource/role fields are forbidden. Model code reads train/validation records; split-integrity checks access only test identity/time metadata. No test probabilities, labels for evaluation, metrics, explanations or calibration were produced.

Raw data, processed Parquets and every Day 9–10 artifact were hashed before/after execution and remain unchanged. The original four fitted models are reused, not reselected against test data.

## Model comparison and optimization

All six families are assessed on exactly the same 1,752 validation cases. Prevalence estimates the positive training proportion; elapsed baseline uses only prefix time. Logistic regression and tree retain their approved configurations. New models use the same six-column input contract; the two baselines intentionally ignore unused columns.

Learned preprocessing is fitted exclusively to each fitting subset. Elapsed time uses median imputation, log1p and standardization. Activities and calendar categories use explicit missing handling and one-hot encoding with unknown categories ignored. Schema validation restores approved column order and rejects extra fields. Unseen values and missing values are tested.

Advanced parameter choice uses three **expanding, purged folds inside the original training partition**, not shuffled cross-validation:

| Fold | Assessment starts UTC | Fit after purge | Assessment cases | Purged fit cases |
|---|---|---:|---:|---:|
| 1 | 2018-01-17 09:56:03 | 2,183 | 1,156 | 130 |
| 2 | 2018-03-09 08:52:06 | 3,300 | 1,157 | 169 |
| 3 | 2018-04-29 17:59:05 | 4,436 | 1,157 | 190 |

Cases sharing a prediction time stay together. A fitting label's observed endpoint must be strictly before the assessment cutoff. A new preprocessing pipeline is fitted per fold. The target cutoff remains the previously approved outer-training-derived target; it is not estimated afresh within each inner fold. Thus these inner results optimize an inherited fixed research target, rather than simulate discovery of a new target prospectively.

| Candidate | Mean inner AP | SD across three temporal blocks |
|---|---:|---:|
| Forest depth 5 | .354834 | .007140 |
| Forest depth 8 | .356739 | .010052 |
| Boosting depth 1 | .346167 | .017637 |
| Boosting depth 2 | .361773 | .013756 |

Select depth within each advanced family by mean AP, then Brier score and lower complexity for ties. Fit each winner on all original training cases. Temporal-block variability is descriptive, not a confidence interval.

Configurations (seed 42):

- Prevalence: `DummyClassifier(strategy='prior')`.
- Elapsed baseline: logistic regression C=1, max_iter=2000, tolerance 1e-8.
- Full logistic regression: C=.1, max_iter=2000, tolerance 1e-8.
- Decision tree: depth 4, minimum 100 observations per leaf.
- Random forest: 120 trees, selected depth 8, minimum 30 observations per leaf, sqrt feature sampling, bootstrap sample fraction .8, one worker.
- Gradient boosting: 100 stages, learning rate .05, selected depth 2, minimum 30 observations per leaf, subsample 1, no internal random early-stopping split.

All full estimator parameters, preprocessing descriptions, search results and fold cutoffs are saved in `outputs/models/day11_12/validation_report.json`. Python 3.12.0, scikit-learn 1.9.1, joblib 1.6.0, threadpoolctl 3.7.0; complete environment pins are in `requirements.txt`. Manifests record sklearn/NumPy/Pandas versions and hashes. No packages were added for Days 11–12.

## Actual validation results

Initial comparison uses **p ≥ .50** for every model. Positive means historically long-running. AP and ROC-AUC use probabilities; AP is average precision, not trapezoidal PR area. Brier is mean squared probability error (lower is better). Precision is zero when no positive prediction is made.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | AP | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prevalence | .716895 | .000000 | .000000 | .000000 | .500000 | .283105 | .205965 |
| Elapsed baseline | .729452 | .775000 | .062500 | .115672 | .554053 | .377694 | .200709 |
| Logistic regression | .726027 | .673913 | .062500 | .114391 | .672844 | .465132 | **.189335** |
| Decision tree | .728311 | .884615 | .046371 | .088123 | .605747 | .356588 | .194993 |
| **Random forest** | .725457 | .894737 | .034274 | .066019 | **.685464** | **.483776** | .192673 |
| Gradient boosting | .728311 | .916667 | .044355 | .084615 | .669721 | .476044 | .191049 |

Common-.50 confusion matrices are stored in the report, rows actual negative/positive, columns predicted negative/positive. Forest: `[[1254,2],[479,17]]`. Low recall at .50 shows why accuracy alone is misleading.

**Selected: random forest.** Its AP exceeds the best simpler model (logistic regression) by **.018644**, and the strongest baseline (elapsed) by **.106082**. The explicit descriptive complexity hurdle is .01 absolute AP over the best simpler model; if unmet, the simpler model is retained. This is a practical selection rule, not a significance test or proof of operational benefit. Boosting AP is .007732 below forest. Logistic regression remains easier to interpret and has better Brier score; the forest does not win every metric. Its selection follows the requested AP priority.

Each model also has a separate exploratory threshold selected by validation F1 on .01:.01:.99; ties favor proximity to .5 then the larger threshold. Forest's saved threshold is **.22**: precision **.381565**, recall **.717742**, F1 **.498251**, confusion `[[679,577],[140,356]]`. This identifies more historical positives while producing many false alarms. There is no cost-based threshold justification. Model choice, threshold choice and explanations reuse validation, so results are optimistic relative to independent final testing. The locked test remains necessary for a later authorized final assessment.

Reliability diagrams use actual validation probabilities and quantile bins, accompanied by Brier and bin counts. They are diagnostics, not evidence that calibration was corrected. No calibrator was fitted.

## Global explainability

Permutation importance shuffles each of the **six original columns** through the exact saved selected pipeline and measures validation AP reduction. Categorical dummy columns are never separately shuffled. Ten repetitions, seed 42, report mean, population SD and min/max; negative drops are retained. The chart's error bars indicate shuffle variability, not confidence intervals.

| Original feature | Mean AP drop | Shuffle SD |
|---|---:|---:|
| Prefix elapsed hours | .080414 | .003428 |
| UTC weekday | .062441 | .011010 |
| Second activity | .056357 | .007576 |
| UTC month | .036413 | .006783 |
| UTC hour | .006772 | .005031 |
| First activity | .000000 | .000000 |

The model relies most on early elapsed time, weekday and second activity for validation ranking. First activity contributes no measurable permutation value here; this does not prove it is unimportant in the real process. Correlated features may share/substitute predictive information. Calendar patterns can encode cohort differences or drift.

Recomputing seed 42 reproduces every permutation result exactly. A second ten-repeat run with seed 43 gives feature-rank correlation **1.0**, the same leading feature, and maximum mean-drop difference **.004336**. This assesses seed sensitivity on the same validation cohort, not stability across populations.

Native tree importance remains supplementary. Inspecting logistic regression still shows its encoded coefficients and correct scaled/log-transformed interpretation, with exact additive log-odds explanations. Coefficients and native importance are not substituted for grouped permutation evidence. Background on permutation limitations: [scikit-learn documentation](https://scikit-learn.org/stable/modules/permutation_importance.html).

## Local explainability and fidelity

SHAP is not installed. Rather than add SHAP/Numba dependencies, the implementation directly enumerates the **exact grouped empirical interventional Shapley game** for six original inputs. This is a faithful probability explanation, not a fabricated approximation or a claim that the SHAP package is incompatible. The saved pipeline itself predicts every hybrid input, so encoding and original groups remain aligned.

Let B be 32 training rows sampled without outcome selection using seed 42. For each of 64 feature subsets S, v(S) is the mean predicted probability after replacing columns S in B with the selected case values. Each feature contribution is the Shapley-weighted average of v(S ∪ {j}) − v(S), weight |S|!(6−|S|−1)!/6!. Therefore v(empty) plus six contributions equals the exact case probability. No approximation over coalitions is used; the empirical background is deliberately small and its choice affects attribution. There is no log-odds/probability scale confusion.

The background is training-only. No validation or test cases are used to choose it. Case IDs never enter it. Original-feature masking can create unrealistic activity/calendar combinations; correlated predictors and alternate backgrounds can change allocations. Explanations describe this fitted model relative to this reference, not causes or what an intervention would achieve.

Three validation cases chosen by position (first, middle, last) were checked: declarations **110775**, **120543**, **142881**. Each had **0.0 observed reconstruction error**, exact repeated-call equality, and matching reloaded-model probability. Synthetic tests also verify known additive-game contributions, dummy features, all six model families, finite values and exact feature mapping. Reconstruction alone does not prove causal validity or robustness to background choice.

### Real example: declaration 110775

First event: Submit Employee, 2018-07-13 08:08:03 UTC. Second: Approved Administration, 08:08:06 UTC. Prefix elapsed: **3 seconds** (.000833333 hours). UTC month 7, weekday 4 (Friday), hour 8. The actual observed outcome is negative, used only after prediction for evaluation.

| Probability decomposition | Percentage points |
|---|---:|
| Training-background mean risk | 23.044472 |
| First activity | +0.000000 |
| Second activity | +0.158876 |
| Prefix elapsed hours | −1.818109 |
| UTC month | +2.815830 |
| UTC weekday | +1.679939 |
| UTC hour | −0.972304 |
| **Predicted risk** | **24.908704%** |

At .22 this is a **false positive**; at .50 it is negative. Moving the threshold changes the class, not risk or contributions. The largest allocation is July's positive month term relative to the selected training background. It does not prove July causes delays.

## Dashboard and beginner walkthrough

Start from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
# Existing artifacts are ready; this command reproducibly regenerates v2 only:
.\.venv\Scripts\python.exe scripts/run_day11_12.py
.\.venv\Scripts\python.exe scripts/verify_advanced_artifacts.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the URL printed by Streamlit (normally http://localhost:8501). A verified instance was run at http://localhost:8506. Existing Day 9–10 artifacts are required by the advanced script; do not regenerate earlier data to change figures. Predictive Analytics shows the frozen modeling population; historical sidebar cohort filters do not redefine it.

1. Choose **Predictive Analytics**. Confirm 5,783 training, 1,752 validation, preferred Forest, AP .484 and locked-test count 2,001.
2. In **Model comparison**, leave common .50 and average precision selected. Six actual results appear. Switch the metric to Brier: lower is better and logistic wins this diagnostic. The threshold-policy menu optionally shows separately labeled validation-F1 classifications.
3. In **Validation evaluation**, inspect confusion counts, class distribution, ROC, PR and calibration. At forest's default .22, the confusion matrix is TN 679, FP 577, FN 140, TP 356.
4. In **Case prediction explorer**, select declaration 110775 and Random forest. Risk is 24.9%; actual outcome is not long-running, making the .22 classification incorrect. Only the early inputs enter prediction. Other models show their own risks and explanations.
5. In **Decision threshold explorer**, move probability threshold to .50. Recall falls to .034275, precision rises to .894737; risk probabilities and fitted models remain unchanged. Return to .22 to restore the exploratory saved setting.
6. In **Explainable AI**, choose Global explanations to inspect six-column AP loss with error bars. Global XAI always describes the saved selected forest, even when Inspect model elsewhere is changed.
7. Choose Local explanations, select declaration 110775, and confirm the decomposition above. This section has its own explicitly labeled threshold control; the reference-risk decomposition is independent of either threshold.
8. Choose Analytical evidence, download JSON and inspect `facts.case`, model hash, limitations and `provenance.test_evaluated=false`. The export does not generate recommendations.
9. Read **Research interpretation** for computed AP gains and limitations. Visit Performance Investigation for historical duration evidence, and Process Mining/Case explorer for early sequence context. Feature reliance alone establishes no bottleneck or inefficiency.
10. Resize to a narrow window. Tabs can scroll horizontally, tables scroll within their containers, and chart labels remain readable. Browser refresh reloads the saved pipelines, never retrains them.

## Future LLM evidence interface

`smartbpm.ml_xai.analytical_evidence(...)` returns JSON schema version 1.0; optional case must be a unique eligible validation ID. Files: `day11_12_analytical_evidence.json` (global) and `day11_12_example_evidence.json` (first validation case). UI downloads regenerate selected-case evidence from the same artifact.

```text
schema_version, purpose
facts
  model: family/name/version/selected_model_sha256
  prediction_definition: Event-2 landmark, positive class, duration cutoff,
                         probability threshold, approved six features
  validation_metrics_at_common_0_5, validation_metrics_at_saved_f1_threshold
  global_importance: feature, mean/SD/min/max AP drops
  process_mining_references: local paths, scope, availability, SHA-256
  case: null or display ID, timestamp, Event-2 inputs, risk/class,
        evaluation-only outcome, correctness, faithful decomposition
interpretations: bounded predictive scope and measured AP difference
limitations
provenance: source hash, partition identity hash, chronology/purging,
            background source, test_evaluated=false
prohibited_inferences
```

Historical evidence references point to transition, performance-investigation and methodology reports; they do not assert case-specific causal evidence or retrieve process records automatically. A later authorized stage must verify provenance/freshness and combine supporting process evidence before drafting any recommendation. Facts and interpretations are separated. No LLM call, retrieval/RAG system or recommendation generation exists here.

## Implementation and artifacts

- `src/smartbpm/ml_advanced.py`: training-only temporal search, six-model comparison, versioned persistence/integrity/reload checks.
- `src/smartbpm/ml_xai.py`: grouped permutations, exact original-feature Shapley explanations, stability and evidence export.
- `src/smartbpm/ui_xai.py`, enhanced `ui_predictive.py`: integrated controls, threshold exploration, global/local/evidence views and computed interpretation.
- `scripts/run_day11_12.py`, `verify_advanced_artifacts.py`, `verify_advanced_browser.py`: execution, independent audit and real-browser verification.
- `tests/test_advanced_xai.py`, updated predictive integration in `tests/test_ml_training.py`.
- `outputs/models/day11_12`: all six pipelines, separate selected pipeline, schema, hashed manifest, training background, six-model validation predictions, full comparison/calibration/search/fidelity report and permutation values.
- `outputs/reports/day11_12_*`: human-readable comparison CSV, repeat-level importance/separate-seed results, evidence JSON, runtime/protected hashes and independent audit.
- `outputs/reports/browser_checks/day11_12`: browser verification JSON, desktop/mobile screenshots and verified downloaded evidence.

Versioned v1 artifacts remain under `outputs/models/day9_10`. Rerunning v2 replaces its own derived artifacts only. Joblib loading is intended for trusted locally generated artifacts, with manifest/data integrity checks; it is not an external model-upload interface.

## Verification and limitations

Before modification: **134 tests passed**, one existing optional PM4Py accelerator warning; pip check passed. New focused suite: **8 passed** after correcting a reusable metadata-default assumption exposed by synthetic data. Final full suite: **142 passed, zero failed, one existing optional PM4Py accelerator warning, 237.36 seconds**. `python -m pip check`: no broken requirements. No new dependency was needed.

Independent count/rank/grouped-precision formulas reproduce every model's AP, ROC-AUC, Brier and confusion-derived metrics at .50 and its saved F1 threshold within 1e-12. Permutation mean/SD reproduce raw repeat columns. Training-background identity/values, saved-model probabilities and protected hashes are checked independently.

Real headless Edge verified six model selections, comparison policy/metrics, five evaluation charts, threshold changes, real local selection (declaration 142881, risk .1489302524), artifact-bound JSON download, six mobile tabs at 390px, and navigation to all eight preexisting pages. Final browser run recorded zero rendered exceptions and zero browser-console errors. Screenshots were visually inspected. An initial automation focus/rerender race was corrected; it was not an application slider defect. A long mobile chart-axis title was shortened after visual inspection. Simulated mobile is not a physical-device or accessibility certification; old-page navigation is a regression smoke check, not a repeat of every historical interaction.

During a deliberate Windows server restart, the old process emitted a socket connection-reset shutdown traceback. The replacement Streamlit process and subsequent browser session were checked separately. Browser automation now waits for the selected model's displayed risk and scrolls controls into view before pointer interaction; intermediate harness failures are retained separately from the final verification record.

Remaining research limitations: repeated use of validation for development, moderate AP and precision, many false positives at the F1 threshold, forest Brier worse than logistic, no independent final test assessment, no uncertainty interval for model gain, temporal drift, censoring and eligibility selection, small fixed Shapley background and unrealistic hybrids under dependence. No causal, intervention, live-inference or production-readiness claim is justified. Dataset source hash and all v1 files remain unchanged. No test-set evaluation was performed.

Days 11–12 prepare a verified evidence interface for controlled future work. Stop here: Days 13–15 require explicit user approval.
