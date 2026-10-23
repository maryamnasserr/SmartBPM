# Days 7–8: leakage-safe dataset preparation

This implementation prepares historical labels and a chronological evaluation dataset. No classifier, predictions, recommendation engine, simulation, LLM or agent was implemented. The original XES and cleaned Parquet are read-only; SHA-256 hashes are recorded and checked by the preparation script.

## Reproduction and artifacts

From the repository root, using the existing Python 3.12 environment:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_ml_dataset.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

- `src/smartbpm/ml_features.py`: canonical prefix extraction, safe features, eligibility, explicit-threshold labels, schema validation, leakage audit, train-only preprocessing specification and transformation.
- `scripts/prepare_ml_dataset.py`: deterministic dataset/report generation and read-back verification.
- `data/processed/domestic_declarations_ml_ready.parquet`: 9,536 unresolved snapshots, six predictors, case ID, three timestamps, historical label and partition. Only the six-name `FEATURES` allowlist may enter a model.
- `data/processed/domestic_declarations_ml_audit.parquet`: all 10,500 cases, exclusion reason, historical outcomes/endpoints/counts, split and first/second recorded resource/role attributes. This entire file is forbidden as a model matrix.
- `outputs/reports/day7_8_eligibility_audit.json`: reconciliation, exclusion IDs, endpoint sensitivity and tie/zero-span diagnostics.
- `outputs/reports/day7_8_feature_dictionary.csv`: source, type, availability, transformation, missing handling, risk and inclusion decisions.
- `outputs/reports/day7_8_threshold_derivation.json`: training reference IDs, threshold source, quantile and historical comparison.
- `outputs/reports/day7_8_split_summary.json`: boundaries, counts, class distributions, prediction ranges and overlap diagnostics.
- `outputs/reports/day7_8_leakage_audit.json`: leakage checks, forbidden inputs and missingness by partition.
- `outputs/reports/day7_8_preprocessing_spec.json`: training IDs, numerical imputation/scaling statistics and categorical vocabularies. This fits preprocessing only, not a classifier.
- `outputs/reports/day7_8_runtime.json`: measurements, sizes and unchanged source hashes.
- `src/smartbpm/ui_ml.py`, `app.py`: read-only ML Preparation navigation section; preparation statistics use the frozen full dataset and are explicitly independent of cohort filters.
- `tests/test_ml_features.py`: synthetic known-answer, mutation, corruption, reproducibility and actual-data integration tests.
- `scripts/verify_ml_browser.py`: actual Edge CDP smoke verification; uses Streamlit port 8503 and Edge debugging port 9223.

Generated processed datasets are ignored by the existing `.gitignore`; regenerate them locally rather than assuming a clone contains them. Reports contain source case identifiers for auditing and should be handled as research data.

## Target and operational snapshot

The exact historical target is `1[(last recorded UTC timestamp - first recorded UTC timestamp)/86400 seconds > 11.105428240740741 days]`. Equality is negative. It predicts total **observed elapsed span**, including waiting, not remaining duration, certified completion, active work time or breach of an official SLA.

The prediction point is immediately after receipt of the second recorded event. Events are ordered by case ID, UTC timestamp and unique original `_source_order`. Exactly two rows contribute features, even if later rows share their timestamp. An online implementation needs equivalent reliable ingestion ordering; source-order ties do not establish causal precedence. Duplicate IDs or identical event records remain separate observations when source rows differ; duplicate source provenance or invalid required attributes/timestamps fail explicitly. Case identifiers remain unchanged strings.

## Reconciliation with Day 6

Day 6's 10,366 was landmark reachability, not the final unresolved evaluation cohort. Its threshold was already training-only: `performance.temporal_design` first split by prediction timestamp, purged overlapping observed endpoints and computed the remaining training p75. The full-log p75 of 12.241634837962962 days was descriptive; it did not define the selected target. There is no global-threshold leakage defect to correct. Recomputed values match Day 6, so the threshold and research target are unchanged.

| Accounting group (mutually exclusive) | Cases | Treatment |
|---|---:|---|
| Fewer than two events | 134 | Never reach prediction point; excluded |
| Already strictly over threshold at Event 2 | 333 | Known positives; separate operational group |
| Additional overlapping outcomes | 497 | Excluded from unresolved evaluation |
| Unresolved, mature chronological snapshots | 9,536 | Final ML-ready rows |
| Total original cases | 10,500 | Fully reconciled |

`10,500 − 134 = 10,366`; `10,366 − 333 = 10,033` unresolved before overlap purging; `10,033 − 497 = 9,536` final rows. Day 6's 520 overlap cases include 23 of the 333 known positives. Exclusion priority is singleton, known-positive, overlap, then unresolved; overlap and known-positive flags are also preserved independently. No double-counting occurs.

All 134 singleton cases have zero observed duration. There are no zero-duration Event-2 cases in these data; synthetic two-event zero-span cases are retained. Ten cases have timestamp ties. Five prediction timestamps equal the final observed endpoint; these are retained unless another stated exclusion applies, because future endpoint knowledge must not define prefix eligibility. The 457 non-payment endpoints are not automatically incomplete and are not removed. Actual completion and censoring are unknown; endpoint-by-eligibility class counts are exported for sensitivity analysis. Dropping singleton negatives changes target prevalence and selection; their counts and zero-span outcomes are explicitly reported.

## Threshold and temporal evaluation

Retain Day 6's 60/20/20 design for comparability rather than introduce an unneeded 70/15/15 redesign. Boundaries are selected by the 60th and 80th percentile positions of sorted Event-2 prediction timestamps; all equal prediction timestamps stay together. Validation begins **2018-06-27T09:27:50+00:00** and test begins **2018-10-12T13:06:56+00:00**.

Before purging, 268 training cases end at or after validation begins and 252 validation cases end at or after test begins. Purge these cases, including equality. Remaining threshold-reference counts are train 5,951, validation 1,821 and test 2,074, with 520 purged. Fit the linear-interpolated p75 using only those **5,951 training durations**, then freeze 11.105428240740741 days for all cases. The reference cohort includes 168 already-over-threshold training cases, as in Day 6. Do not iteratively refit after threshold-dependent known-positive removal: that would change the estimand and create circular selection. The unresolved training cohort for future model/preprocessor fitting is 5,783 cases.

| Final unresolved partition | Cases | Positive | Negative |
|---|---:|---:|---:|
| Training | 5,783 | 1,320 | 4,463 |
| Validation | 1,752 | 496 | 1,256 |
| Test | 2,001 | 668 | 1,333 |
| Total | 9,536 | 2,484 | 7,052 |

Known positives by original partition: train 168, validation 69, test 73, purged 23; all 333 are positive. The additional 497 unresolved purged cases contain 268 positives and 229 negatives. All 10,366 Event-2 cases still reproduce Day 6's 3,085 positives and 7,281 negatives. Their full class distributions are retained in the split report.

Each case has exactly one original partition and at most one final row. Strict ordering and unique IDs are checked. Outcomes are observationally mature before the next cutoff after purging, but a last observed timestamp is not proof of completed or promptly ingested outcome data. This is a retrospective chronological approximation with endpoint purging, not certified strict prospective deployment. Purging uses historical future endpoint information to define the evaluation sample and preferentially removes longer cases; report this bias alongside results. Day 6 already inspected all data for research design, so this is not a never-inspected external test cohort. No test-driven model selection or performance assessment occurs here.

## Approved features and availability

Primary features are `first_activity`, `second_activity`, `prefix_elapsed_hours`, `utc_month`, `utc_weekday` (Monday=0) and `utc_hour`. UTC calendars describe the second event, not an assumed local working calendar. The two activities encode the exact length-two activity history without an additional redundant concatenated feature. Activities and timestamps are required recorded event fields. Missing/blank activities and invalid, naive or absent timestamps fail; no fabricated activity or time is imputed. Required source provenance must be unique and nonnegative. No class/framework dependency was added.

First/second resource and role values are preserved in the audit only. Event scope is known, but historical XES does not prove ingestion-time availability. These are **sensitivity-only** features pending confirmation, with an activity/time-only primary design. Nulls are preserved separately from literal `MISSING`/`UNDEFINED` category strings; missingness is reported. Later-event attributes never enter prefix features.

Exclude all final case attributes (Amount, BudgetNumber, DeclarationNumber, case:id and others), because trace constancy is not evidence of availability at Event 2. Exclude IDs, raw absolute timestamps, source provenance, final duration, endpoint, future count/activities/repetitions/variant, targets and partitions from predictors. Timestamps and case ID in the ML-ready table are explicitly audit/join fields. Future outcomes are stored separately in the audit, apart from the required historical target label. Feature access always uses `feature_matrix` and an explicit allowlist.

The serializable preprocessing specification fits median fallback, means/stds and categorical vocabularies only on unresolved training rows. Zero-variance scale is 1; all-null numerical fallback is 0. No missing numerical values occur in the actual primary data. Unknown later categories map to all-zero indicators; null categories also map to zero while literal strings retain their own vocabulary entries. No feature selection occurs. Future tuning uses validation only; the test is reserved for a single final model assessment. This session audits test label counts as required but computes no accuracy, precision, recall or other predictive performance.

## Verification and limitations

Baseline before edits: **91 passed**, one optional PM4Py accelerator warning, 211.12 seconds. Initial new focused suite: **23 passed** in 18.05 seconds. `pip check` found no broken requirements. The pipeline verifies schema, snapshot consistency, labels, training threshold, label maturity and accounting; reads both Parquets, JSON and CSV back; and checks unchanged source hashes. Repeated runs reproduce rows and reports except measurement metadata. First measured preparation was 6.289 seconds (total 7.241); warm rerun was 1.407 seconds (total 2.488), excluding interpreter imports. ML-ready Parquet is 367,788 bytes, audit Parquet 618,707 bytes. Runtime reports record exact disk headroom and all artifact sizes; timings are local measurements, not guarantees.

Final full regression: **114 passed**, one existing optional PM4Py warning, **199.93 seconds**. Actual headless Edge verification passed for all eight navigation sections, with zero rendered exceptions. ML metrics and three tables matched exported statistics; desktop/mobile screenshots were inspected. Simulated mobile document/viewport both measured 390px. ML navigation took 1.130 seconds. Evidence is under `outputs/reports/browser_checks/day7_8/` (`verification.json`, `ml_desktop.png`, `ml_mobile.png`). Initial sandboxed Edge startups failed; the dedicated hidden browser launched successfully with sandbox escalation. See the development progress log for the final record. No physical-device or cross-browser coverage is claimed.

Remaining limitations: unknown completion/censoring, unverified event attribute arrival times, source-order ambiguity at ties, endpoint-purging selection, weak early signal, drift in historical cohorts and observational labels. No causal interpretation or intervention benefit follows. Next authorized development step should compare prevalence and prefix-elapsed baselines with an interpretable classifier, train-only fitting and validation-based model selection, then evaluate once on the frozen unresolved test set. Days 7–8 stop before classifier training, pending user approval.
