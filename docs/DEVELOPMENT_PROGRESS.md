# Development progress

Current development day: Combined Days 11–12, completed and verified on 2026-10-21 (Africa/Cairo).
Next approved task: none; waiting for explicit approval before further features.

## Days 11–12: advanced ML and explainable AI

Implemented controlled random forest and gradient boosting pipelines, reusing the four frozen Day 9–10 models and original six Event-2 predictors. Three expanding, endpoint-purged training-only folds choose forest depth 8 (of 5/8) and boosting depth 2 (of 1/2). Seed 42; all preprocessing is fitted within fitting subsets. Original target, eligibility and partitions 5,783/1,752/2,001 are unchanged; test remains locked and no test predictions or scores were generated. Protected raw/processed and all v1 artifact hashes remain unchanged.

Selected forest validation AP .483776220 versus logistic .465131832 and strongest baseline elapsed .377694478. Its .018644 AP gain exceeds the explicit descriptive .01 complexity hurdle; this is not a significance claim. Boosting AP .476043832. Forest ROC-AUC .685463806 and Brier .192672675; logistic Brier is better (.189334789). Initial classification comparison uses .50 for all six. Exploratory validation-F1 forest threshold .22 gives precision .381564845, recall .717741935, F1 .498250525, confusion TN 679 / FP 577 / FN 140 / TP 356. Reused-validation optimism, weak precision, calibration and temporal drift limitations are explicit.

Global XAI: ten original-column AP permutation repetitions; elapsed mean drop .080414, weekday .062441, second activity .056357; first activity zero. Seed 42 rerun is exact; seed 43 rank correlation 1.0, maximum mean difference .004336. Local XAI directly enumerates all 64 original-feature Shapley coalitions on the probability scale using 32 fixed training background rows. No SHAP package dependency was added. Three position-selected real validation cases reconstruct exact pipeline risks with observed error 0.0, and repeated calls match. Correlation, unrealistic masked combinations, background dependence and noncausal scope are documented.

Predictive Analytics now has six comparison/evaluation/case/threshold/XAI/interpretation tabs. It exposes global importance variability, faithful local contributions, optional baseline/LR/tree explanations and artifact-bound analytical JSON. Facts, interpretations, process-evidence references, limitations and provenance are separated for future controlled LLM use. No recommendation generation, LLM call, RAG, agent or simulation exists.

Verification: before edits 134 tests passed; focused new suite 8 passed; final full suite **142 passed, zero failed, one existing optional PM4Py accelerator warning, 237.36 s**. Pip check: no broken requirements. Independent rank/count formulas reproduce six-model common and tuned metrics within 1e-12, permutation summaries, training-background identity and exact reload predictions. Synthetic testing found and fixed a metadata-default assumption in the reusable training function. A mobile chart title was shortened after screenshot review. No new dependency was installed.

Real Edge verified six model selections, comparison controls, five evaluation charts, threshold changes, real validation local explanations, downloaded JSON and all eight earlier pages. All six predictive tabs fit a 390px simulated-mobile viewport; final report records zero rendered exceptions and zero console errors. An initial browser focus/rerender race in the harness was corrected. Full details, actual metrics, example false positive declaration 110775, artifact/version inventory, commands and manual walkthrough: [DAY11_12_ADVANCED_ML_XAI.md](DAY11_12_ADVANCED_ML_XAI.md). Models/artifacts: `outputs/models/day11_12`; reports: `outputs/reports/day11_12_*`; screenshots/browser report: `outputs/reports/browser_checks/day11_12`. Streamlit verification port: 8506.

Days 11–12 complete within historical thesis scope. Ready to discuss controlled Days 13–15 evidence integration after explicit approval; independent final test evaluation and any live deployment remain out of scope. Stop here.

## Days 9–10: predictive analytics completed and verified

Implemented reusable sklearn training, evaluation and artifact utilities and the integrated Predictive Analytics page. Models: training-prevalence and elapsed-only baselines, regularized logistic regression (C=.1 selected from .1/1) and a constrained tree (depth 4 selected from 3/4, minimum 100 samples per leaf); seed 42. All learned preprocessing is training-only. Approved Event-2 predictors, the frozen duration cutoff of 11.105428240740741 days, chronology/purging and partitions of 5,783/1,752/2,001 remain unchanged. Modeling accesses train/validation records only; test metadata is checked for partition integrity without test inference, scoring or tuning.

Preferred logistic validation AP .465131832, ROC-AUC .672843737, Brier .189334789; strongest baseline AP .377694478 (elapsed), gain .087437354 absolute. Validation-F1 threshold .20 gives accuracy .594748858, precision .379775281, recall .681451613, F1 .487734488, and TN 704 / FP 552 / FN 158 / TP 338. Same-validation selection/tuning is explicitly exploratory and potentially optimistic. Probability quality is imperfect: mean risk 22.8% versus observed 28.3%, with sparse high-risk bins. No causal or deployment-performance claim. Saved pipelines reproduce identical validation probabilities; logistic additive log-odds and tree leaf/path explanations reconstruct risks.

Baseline before edits: 116 passed, one optional PM4Py warning, 119.42 s. Focused ML suite: 18 passed. Final full suite: **134 passed, zero failed, one existing optional PM4Py accelerator warning, 235.41 s**. Pip check: no broken requirements. Added pinned sklearn 1.9.1, joblib 1.6.0, threadpoolctl 3.7.0 and cloudpickle 3.1.2 only. No convergence warning. An independent rank/count-formula audit reproduces actual AP, AUC, classification and Brier values, thresholds and train-only preprocessing within numerical tolerance; no test scores generated. Source hashes for raw, cleaned, ML-ready and audit files remain unchanged.

Actual Edge: metric/model/threshold/case controls, all five evaluation charts, exact confusion counts, coefficient/tree explanations and all eight existing pages verified. Four predictive tabs fit a 390px simulated-mobile viewport. Clean final run: zero rendered exceptions and zero browser-console errors; cold predictive navigation 15.041 s. Screenshots inspected, including readable contribution labels and the unclipped preferred-model card. Intermediate synthetic test setup/export-index issues and browser readiness/restart-log issues were corrected and disclosed. ML Preparation/Performance messages now distinguish their historical statistics from saved trained-model validation results.

Artifacts: `outputs/models/day9_10/{models.joblib,manifest.json,validation_predictions.parquet,validation_report.json,*_explanation.csv}`; reports and evidence under `outputs/reports/day9_10_*` and `browser_checks/day9_10`. New modules, execution/independent-verification/browser scripts and tests are documented in [DAY9_10_ML_RESULTS.md](DAY9_10_ML_RESULTS.md), with configurations, exact results, real false-positive example declaration 110775 and a beginner walkthrough. Model version 1.0. Execution initially took 11.759 s, and 21.222 s under concurrent testing; dataset hashes unchanged. The dedicated Edge profile was removed after verification; the app remains at http://localhost:8505.

Days 9–10 complete within historical thesis scope. Holdout remains locked for later explicitly authorized final evaluation. Censoring/availability uncertainty, temporal drift, selection bias, moderate precision, probability underestimation and selected-validation optimism remain limitations. No recommendations, simulation, LLM, agent or Day 11 work implemented. Stop awaiting user approval.

## Environment and initial state

Windows PowerShell; workspace C:\Users\Maryam Nasser\Desktop\SmartBPM.
Python 3.12.0 available at C:\Program Files\Python312\python.exe; Python 3.14.6 also listed by launcher. Initially only data/ and Microsoft/ were present; no existing application, virtual environment, Git repository or applicable AGENTS.md found. Existing folders and raw data preserved.

Created .venv with Python 3.12.0. Installed PM4Py 2.7.23.11 and Pytest 9.1.1, with Pandas 3.0.6 and NumPy 2.5.4 as dependencies. Exact full versions recorded in requirements.txt. Git initialized; no commit made. Verified raw dataset, .venv and .env are ignored.

## Completed files and folders

Created data/processed, outputs/reports, outputs/models, outputs/simulations, src/smartbpm, scripts, tests, docs.
Created src/smartbpm/__init__.py, src/smartbpm/dataset.py, scripts/inspect_dataset.py, tests/test_dataset.py, pyproject.toml, requirements.txt, .gitignore, README.md and this progress file.
Generated outputs/reports/dataset_profile.json and outputs/reports/inspection_console.txt (human-readable full profile).

## Observed dataset

Original data/raw/DomesticDeclarations.xes: 20,497,405 bytes.
SHA-256: b681556df88103c13beceb448b66501d26e92d65cc90c185c21affa2aa607b9f.
10,500 traces/cases; 56,437 events; 17 activities; zero empty traces.
UTC timestamps: 2017-01-09T08:49:50+00:00 to 2019-06-17T15:30:58+00:00.

Original event attributes: id, org:resource, concept:name, time:timestamp, org:role.
Original trace attributes: id, concept:name, BudgetNumber, DeclarationNumber, Amount.
Flattened schema: five event fields plus case:id, case:concept:name, case:BudgetNumber, case:DeclarationNumber, case:Amount. String fields, UTC datetime timestamp and float64 amount. All ten flattened columns have zero null values; original event and trace attributes have no absent values.
Activities and their exact frequencies, types, missing counts and five actual records are in the JSON report. Examples include Declaration SUBMITTED by EMPLOYEE, Request Payment and Payment Handled. UNDEFINED is an observed role label, not a null; no semantic reinterpretation applied.

## Decisions and preprocessing

Reusable Python module with thin CLI; no notebooks or web stack needed on Day 1. Native PM4Py XES importer used. No records excluded, sorted, imputed or deduplicated. UTC used for timestamp summaries. Required identifiers, activity names and timestamps validated; optional attributes profiled. No activity start timestamps, processing durations, individual worker capacities or SLA thresholds inferred. Preserve source; derived outputs stored separately.

PM4Py conversion mutates in-memory event attributes by adding trace fields. Conversion now receives a deep copy so the original event and trace attribute scopes remain inspectable; regression test added.

## Actual validation

Commands run from the workspace with .venv/Scripts/python.exe:
- python -m pip check: No broken requirements found.
- python scripts/inspect_dataset.py: exit 0; real XES loaded, structured report and console sample saved.
- python -m pytest -q: final run 15 passed, 0 failed, 1 warning in 22.95 seconds. Includes real-data integration, synthetic loading, original attribute scopes, required-field failures, empty/malformed/missing files, CLI errors and source-overwrite protection.
- git check-ignore data/raw/DomesticDeclarations.xes .venv/ .env: all ignored.

Initial 14-test run passed; report review revealed the PM4Py mutation noted above. Corrected it, regenerated profile and passed all 15 tests.

## Errors, limitations and risks

Sandbox denied workspace access and commands initially started in C:\; stopped broad searches, used explicit location and escalated workspace operations. Dependency download/installation was slow but completed successfully.
PM4Py emits an optional r4pm performance warning; standard loading works. No optional accelerator installed. Empty folders are present locally but not tracked by Git until they contain files. Generated report includes five actual records and is intended for local thesis use; review before external publication.

## Day 1 handoff (historical)

Day 1 acceptance criteria met. Day 2 preview: data-quality checks and documented preprocessing, then initial process exploration and variants within the approved roadmap. No Day 2 implementation, ML, simulation or agents started. Await user confirmation.


## Day 2: completed

User explicitly approved Day 2 only. Inspected the Day 1 structure, reusable loader, inspection CLI, tests, README, requirements and this progress file. Preserved existing behavior and reused Pandas, PM4Py and Matplotlib. Added PyArrow 26.0.0 only for Parquet; updated the complete exact requirements snapshot. No ML, recommendation engine, simulation, LLMs, agents or dashboard implemented.

### Files created or modified

Created src/smartbpm/preprocessing.py (mapping, timestamp validation, XML audit, quality checks, deterministic ordering), src/smartbpm/exploration.py (observed process statistics/tables/charts), src/smartbpm/day2.py (orchestration and preservation checks), scripts/run_day2.py, tests/test_day2.py and docs/DAY2_METHODOLOGY.md.
Modified src/smartbpm/dataset.py only to support optional keyword validation, retaining strict Day 1 behavior by default. Modified README.md, requirements.txt and this progress log.

Generated data/processed/domestic_declarations_cleaned.parquet; outputs/reports/data_quality_report.json, preprocessing_report.json, initial_eda_summary.json; nine CSV tables and seven PNG charts, whose names are listed in the EDA summary and methodology. Existing Day 1 reports preserved. No Git commit made.

### Actual quality findings

10,500 cases, 56,437 events, 17 activities; no missing values in the ten original flattened columns. No invalid required values, invalid observed types, exact duplicate rows, duplicate event IDs, duplicate trace case names, empty traces, inconsistent case attributes or backward timestamp steps.
Twenty timestamp-tied events across ten cases, retained with source-order tie-breaking. Original offsets: +01:00 for 23,676 events, +02:00 for 32,761; all valid and aware. Offset variation alone does not establish a timezone defect.
Trace lengths: 1 to 24, mean 5.375, median 5; 134 single-event cases. IQR length fences 3.5/7.5 flag 365 shorter and 918 longer cases, without removal.
1,019 cases repeat at least one activity; 1,759 excess activity occurrences; no adjacent equal activities. Repetition is not treated as record duplication.
Resources: STAFF MEMBER 36,353; SYSTEM 20,084. Broad labels do not identify workers or capacities.

### Preprocessing and outputs

No record-level cleaning needed. No deletion, deduplication, imputation, label normalization or amount coercion. Explicit mapping; valid aware timestamps normalized to UTC. All original attributes preserved. Added zero-based _source_order for provenance; deterministic case/timestamp/source-order sort. Source XES order recoverable. Full Parquet read-back equality and source SHA-256 checked successfully. The source fingerprint matches Day 1.
Analytical Parquet has 56,437 rows and 11 columns (ten original plus provenance); file size 1,704,002 bytes.

99 observed variants. Leading variant 4,618 cases (43.98%); next two 2,473 and 1,392. Observed elapsed duration: mean 11.526 days, median 7.330, p95 29.205, max 469.236. Duration includes waiting and unobserved intervals, not active processing time.
Starts: submitted 10,365, saved 135. Ends: Payment Handled 10,043; employee rejection 284; saved 134; MISSING rejection 30; administration rejection 5; supervisor rejection 4. All 457 non-payment endpoints retained; no definitive complete/incomplete labels inferred.

### Commands and actual tests

From C:\Users\Maryam Nasser\Desktop\SmartBPM:
- .venv/Scripts/python.exe -m pip install pyarrow: installed 26.0.0.
- .venv/Scripts/python.exe -m pip freeze: exact requirements.txt refreshed.
- .venv/Scripts/python.exe -m pip check: No broken requirements found.
- .venv/Scripts/python.exe scripts/run_day2.py: final run exit 0; all real-data outputs generated; source fingerprint and Parquet read-back equality verified.
- .venv/Scripts/python.exe -m pytest -q: final result 42 passed, 0 failed, 1 optional PM4Py performance warning in 50.74 seconds. Includes all original 15 tests plus 27 Day 2 tests/parameter cases.

Tests cover required schema, null/non-string/blank required identifiers and activities, invalid/naive/numeric timestamps, timezone equivalence, source-order tie-breaking, event/case/attribute preservation, distinct duplicate definitions, conflicting/missing case attributes, mapped column names, reserved provenance, independently calculated durations/variants/repetitions/endpoints, raw XML offsets, output generation, strict JSON, deterministic output hashes, raw-output path protection, naive-source refusal with saved diagnostics and real-data end-to-end integration.

### Errors and resolutions

The patch tool failed during writes and temporarily truncated the loader. Restored it from the previously inspected source, used PowerShell file writes and verified all original tests afterward.
The first pipeline run failed with no space left on C:; Windows reported zero free bytes and prevented test-file creation. Used pip cache info and removed only disposable pip downloads via pip cache purge (79 cached files; about 91 MB freed). Dataset, project files and installed packages retained. Reran the pipeline successfully.
Initial suite: 37 passed, 1 failed because a one-case synthetic log has undefined standard deviation and strict JSON rejects NaN. Converted undefined descriptive statistics to JSON null. Targeted synthetic reproducibility test then passed; expanded validation and final full suite passed 42 tests.

### Limitations and next approved task

Remaining disk headroom is limited; more space is needed before subsequent development. PM4Py optional r4pm accelerator warning remains; loading works without it. Checks cannot prove real-world correctness or completeness. Timestamp ties leave causal ordering unknown in ten cases. Observed durations may be censored. Endpoint and IQR flags are descriptive, not defects or completion labels. No processing-time, SLA, resource-capacity or causal assumptions introduced.

Day 2 acceptance criteria met. Waiting for explicit user approval before any Day 3 work. No Day 3 task approved.


## Day 3: interactive application completed

User explicitly authorized a Streamlit application with Plotly, functional filters, tests and browser verification, stopping after Day 3. Inspected dataset.py, preprocessing.py, exploration.py, day2.py, dependency versions, existing tests, progress and configuration. Reused quality_report and describe_process; Day 1/2 modules and analytical outputs were not changed.

### Files and features

Created app.py; src/smartbpm/dashboard.py; src/smartbpm/dashboard_charts.py; tests/test_dashboard.py; .streamlit/config.toml; scripts/verify_dashboard_browser.py; docs/DAY3_APPLICATION.md.
Updated README.md, requirements.txt and this log.
Generated outputs/reports/dashboard_browser_verification.json and dashboard_desktop.png, dashboard_activities.png, dashboard_variants.png, dashboard_mobile.png. These screenshots document the UI and are never chart inputs. Earlier reports remain intact.

Five navigation views: Overview; Activities & resources; Variants & repetition; Case boundaries; Case explorer. Eight interactive Plotly figures are built directly from selected analytical tables: activity/resource counts, observed elapsed duration, trace length, top variants, repeated activities, starts and ends. Includes exact variant sequences in hover/table, complete variant table, case selection, case events and selected-case CSV download. Responsive light teal theme; mobile columns stack and navigation collapses into the sidebar.

Full-dataset reference totals and UTC event range remain visible. Selected-cohort metrics and every chart/table use the same complete-case cohort. Activity/resource values combine with OR within each control and AND across controls; different events can satisfy activity and resource matches. Date bounds inclusively apply to UTC case start, and duration bounds inclusively apply to full observed elapsed days. Empty activity/resource selections show zero results safely; Reset restores all cases. Incomplete date selection requests both endpoints. This contract prevents event filtering from truncating durations, variants or endpoints.

Read-only loading validates Parquet schema, quality and unique nonnegative source-order provenance. Data paths are anchored to app.py. Cached dataset keys include file path, modification time and size; bounded analysis/cohort caches depend on input data and filter values. No source files, processed events or earlier analytical outputs are rewritten by the interface.

### Dependencies and disk resolution

Installed Streamlit 1.66.0 and Plotly 7.1.0 plus resolved dependencies. Streamlit's Pillow<13 constraint resolved Pillow 12.3.0, replacing 13.0.0. Full resolved environment recorded in requirements.txt. pip check: No broken requirements found.

The first installation exhausted disk space. Removed only regenerable .venv *.pyc caches after checking every target stayed under the virtual-environment root (about 120 MB). Retried without download caching/bytecode compilation; installation succeeded. Used PYTHONDONTWRITEBYTECODE=1 for verification processes to reduce disk pressure. No dataset, earlier reports, source modules or installed package source were removed. Browser verification used a separate temporary Edge profile; background processes initially kept it locked, so only processes identified by that dedicated profile and their descendants were stopped before removing it. Temporary profile cleanup succeeded; about 81 MB remained afterward. Disk space is still limited.

### Actual automated verification

From C:\Users\Maryam Nasser\Desktop\SmartBPM:
- .venv/Scripts/python.exe -B -m pytest -q tests/test_dashboard.py: 11 passed in 57.49 seconds (initial dashboard-focused run).
- .venv/Scripts/python.exe -B -m pytest -q: final expanded run 53 passed, 0 failed, 1 optional PM4Py performance warning in 204.74 seconds. All previous 42 tests pass with the new dependencies.
- .venv/Scripts/python.exe -B -m pip check: No broken requirements found.
- .venv/Scripts/python.exe -B -m pip freeze: updated requirements.txt.

Dashboard tests cover independent cohort count/duration oracles, full-case activity/resource matches on different events, date/duration inclusivity, empty selections, input immutability, required processed schema, missing files, invalid provenance, Plotly trace values/serialization, original XES and Parquet fingerprints and actual app execution with Streamlit AppTest.

AppTest loaded the real dataset and displayed 10,500 cases, 56,437 events, 17 activities. It navigated all five views, selected one full case via a rare activity, tested empty activity/resource selections and reset, tested SYSTEM resource filtering, compared a one-day case-start filter with an independent pandas count and tested a restricted duration range. No application exceptions.

### Actual server and browser verification

Started .venv/Scripts/python.exe -B -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --server.fileWatcherType none. Streamlit started successfully; /_stcore/health returned HTTP 200 and ok. Local app remains available at http://localhost:8501 at handoff. Standard launch command is python -m streamlit run app.py after activating .venv.

Opened the actual local application in a hidden headless Microsoft Edge browser via CDP. Browser assertions and saved evidence show:
- Full cohort metrics: 10,500 cases, 56,437 events, 17 activities, median 7.33 days.
- Overview rendered real Plotly histogram and bar traces; activity chart contained 17 bars.
- Activities/resources, variants/repetition and starting/ending views rendered Plotly figures.
- Pointer drag zoom changed the chart axis range.
- Keyboard duration-slider interaction changed the cohort to 10,328 cases and 56,190 events, with median 7.35 days. Reset restored 10,500 cases.
- Simulated mobile viewport 390px and document width 390px; no horizontal page overflow.
- Zero rendered Streamlit exception elements.

Inspected saved desktop, variants and mobile screenshots directly. Browser-script development initially needed readiness and selector adjustments: document.body can be null during navigation; this Streamlit slider renders native input[type=range] rather than role=slider. Corrected the verification script and final browser run passed. These were verification-selector issues, not app import or data errors.

### Interpretation and limits

Case duration means observed first-to-last elapsed time, including waiting; not active processing time. Frequencies do not prove causal bottlenecks. Repetitions are descriptive possible rework signals, not automatic errors. Non-payment endpoints do not establish incompleteness. Existing timestamp-tie/censoring limitations remain visible in the UI. Resource categories cannot identify individual capacities. Variant ranks/IDs are cohort-local and may change after filtering. Browser coverage is desktop Edge plus simulated mobile width, not physical devices or all browsers. Disk headroom remains low.

Day 3 acceptance criteria met: the real-data Streamlit dashboard launches, interactive charts render, filters work, empty results are safe and all regression tests pass. No ML, recommendations, simulation, LLMs or agents implemented. Stop here; no later feature work approved.


## Combined Days 4–5: completed and verified

User explicitly authorized both stages in one session and requested stopping before Day 6. Reviewed app.py, dashboard/data/chart modules, existing tests and dependency configuration, Day 3 guide and project progress. Baseline full suite: 53 passed, one optional PM4Py warning in 149.91 s; existing application health endpoint returned 200.

### Day 4: measured quality improvements

Profiling showed per-case tuple aggregation constructing thousands of Arrow-backed Pandas groups dominated descriptive analysis. Replaced it with array extraction through group positions and mapped variant IDs using tuples, avoiding per-case JSON serialization. All nine saved Day 2 tables and key summaries remained numerically identical. Chart construction now accepts requested keys, so ordinary pages build two figures rather than all eight; default public behavior remains backward compatible.

Removed injected CSS, used native bordered KPI cards/help, improved hierarchy and visible active-filter context, made activity ticks readable with full names preserved on hover, added inspectable frequency tables and retained responsive navigation. Case/date/resource/activity/duration semantics remain complete-case based. Added explicit finite-bound validation for invalid NaN/infinite duration ranges; vectorized UTC date bounds avoid Python date-object allocation. CSV conversion is reusable, and download clicks avoid unnecessary reruns.

A real-browser regression was found after the initial combined tests passed: deleting filter keys during reset restored Python metrics transiently, but the browser slider retained 0.1 days and resubmitted it on navigation. A downloaded case CSV revealed 10,328 rather than 10,500 cases. Reset now explicitly assigns all widget defaults. Browser checks verified the zero-valued slider, stable restored totals through navigation and exact 10,500-row downloaded case summary. Variant selector/comparison state is reconciled when cohort changes remove old IDs. No warning suppression added.

### Day 5: integrated process mining

Added a sixth Process Mining view using the same case cohort and existing analysis tables. PM4Py frequency DFG backend operates after canonical case/UTC timestamp/source-row ordering, without additional backend sorting or synthetic start times. Counts are independently checked against vectorized adjacency and events-minus-cases conservation.

The interactive Plotly map uses directed curved arrows, activity-code legend/full-name hover, occurrence-scaled widths, optional count labels, seed-stable layout and explicit edge coverage. Minimum frequency, maximum edge count and focus controls hide only existing edges; no dropped intermediate events or fabricated adjacency. All activity nodes remain visible. Hidden-edge performance statistics remain inspectable, and displayed/full transition exports are distinct.

Added variant duration statistics/selection/distributions, repeated activity/approval/rejection groups, elapsed-duration comparisons and exact CSV summaries. A second formal process model was deferred in favor of clear, verified DFG semantics; no BPMN gateways or parallelism invented. No ML, recommendations, simulation, LLMs or agents implemented.

### Files and reproducibility

Created src/smartbpm/process_mining.py, process_mining_charts.py, ui_mining.py; tests/test_process_mining.py; scripts/benchmark_dashboard.py, verify_day4_5_browser.py; docs/PROCESS_MINING_METHODOLOGY.md and DAY4_5_VERIFICATION.md.
Modified app.py, src/smartbpm/dashboard.py, dashboard_charts.py, exploration.py, README.md and this progress log. Dependencies unchanged; no new packages needed.
Generated small day5_transitions.csv, day5_variant_performance.csv, day5_repetition_groups.csv, day5_mining_summary.json under outputs/reports. Recorded baseline/after/runtime measurement JSON and day4_5 browser JSON/screenshots. All original raw/processed data and earlier validated outputs preserved. Data fingerprint integration tests still match Day 2. New screenshots document actual UI verification; they are not chart inputs.

### Actual findings

10,500 cases, 56,437 events, 17 activities, 99 exact variants. DFG: 39 distinct relationships, 45,937 edge occurrences, equal to 56,437 minus 10,500. Most frequent edge final supervisor approval -> Request Payment: 10,038 occurrences, median observed gap 27.43 h, p95 265.30 h. Request Payment -> Payment Handled: 10,037 occurrences, median 77.77 h, p95 146.33 h. Gaps do not separately measure service/queue times.

1,019 cases have repeated activities; median case elapsed duration 13.249 days, versus 7.227 for 9,481 cases without repetition. Repeated-approval-label subset: 276 cases; repeated-rejection-label subset: 150. Subsets overlap, and associations are not causal effects. Leading variant: 4,618 cases (43.98%), median observed duration 7.036 days; second variant: 2,473 cases, median 10.233 days. Tied timestamps remain ordered by original provenance without asserting causality.

### Performance measurements

Three local perf_counter samples per compute operation. Full analysis median 4.084 -> 0.464 s; filtered 1–20 day cohort analysis 3.887 -> 0.442 s. Ordinary Overview chart construction 1.242 s (all eight before) -> 0.183 s (only two after); all eight after still about 1.068 s. Baseline and after loader/filter samples also recorded, but those differences were not isolated implementation improvements and are not claimed as such.

DFG/gap statistics median 0.411 s; 20-edge map construction median 0.133 s. Actual AppTest initial execution 8.167 s; unchanged cached rerun median 0.877 s. First 1–20 day cohort selection 2.767 s; return to full 0.803 s; repeated selection 1.261 s. Compute samples exclude imports/startup; AppTest includes Streamlit execution but not browser rendering. Concurrent verification/system load affects measurements, so these are observations, not production guarantees. Bounded caches preserve memory limits.

### Tests and browser execution

From C:\Users\Maryam Nasser\Desktop\SmartBPM using .venv/Scripts/python.exe with PYTHONDONTWRITEBYTECODE=1:
- Day 4 targeted run: 12 passed in 37.83 s.
- New mining tests: 19 passed in 40.98 s.
- Initial combined full run: 72 passed, 1 warning in 142.21 s.
- After browser-discovered reset fix and readability refinements: targeted 30 passed in 68.12 s.
- Final python -B -m pytest -q: **72 passed, 0 failed, 1 optional PM4Py performance warning in 116.95 s**.
- python -B -m pip check: **No broken requirements found**.
- python -B scripts/benchmark_dashboard.py: runtime report generated; AppTest bare-mode setup emitted missing ScriptRunContext warning, no app exceptions.
- python -B scripts/verify_day4_5_browser.py: final actual Edge run passed.

Unit tests use independent small-log expectations for DFG counts/gaps, ties, singleton/empty logs, self-loops, boundaries/no false bridging, variants/durations, repeated labels, invalid inputs, exact CSV exports and lazy charts. Integration tests compare actual totals, historical numerical artifacts, filter consistency and state changes. Existing tests all still pass.

Restarted only the owned test server after code changes so browser verification used current imports. Actual server started via python -B -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --server.fileWatcherType none; health endpoint 200.

Headless Edge checked all six views, original charts, case inspection, actual downloaded exports, reset persistence and process-map controls. Full KPIs 10,500/56,437/17, median 7.33 days; mining KPIs 45,937 occurrences/39 relationships/99 variants. Default map 17 nodes, 20 edges (21 Plotly traces). High frequency threshold showed a safe no-edge state without changing cohort totals. Variant/repetition tabs opened. Downloaded case summary (10,500 rows), displayed transitions (20) and all transitions (39) exactly matched analytical tables. Pointer zoom changed an axis range. Simulated mobile viewport and document both 390px; no horizontal page overflow or rendered exceptions. Desktop, activity, map and mobile screenshots inspected directly.

Verification helper issues (DOM not yet ready, browser download hub becoming the first tab, and corresponding selector readiness) were corrected. Temporary download copies and the dedicated Edge profile/processes were removed after validation; about 68.7 MB free afterward. No unrelated files deleted. Application remains running at http://localhost:8501.

### Remaining limits and stopping point

Dense maps may need zoom, fewer edges, focus or hidden count labels. DFG is observed adjacency, not formal BPMN semantics. Sparse percentile estimates, tied timestamp order, censoring and broad resource categories limit interpretation. Repetition-duration differences can be confounded. No active processing time, separate queue time, SLA or causal mechanism inferred. Browser coverage is desktop Edge plus simulated mobile viewport, not every browser/physical device. Disk headroom remains limited. The optional PM4Py importer accelerator warning remains; ordinary dashboard operation uses Parquet.

Combined Days 4 and 5 acceptance criteria met. See DAY4_5_VERIFICATION.md for the reviewable report and PROCESS_MINING_METHODOLOGY.md for definitions, assumptions, limitations and primary references. No Day 6 or later work approved. Stop and await explicit user approval.


## Process map readability fix: completed

Replaced the prior Plotly force layout with native interactive ECharts SVG, readable activity/role boxes, deterministic directed layout, default seven-edge main path, all-39-edge mode, optional counts, linked activity inspection, explicit hidden/isolation explanations and real zoom/pan. Full PM4Py discovery and original counts remain unchanged: 10,500 cases, 56,437 events, 17 activities, 39 relationships, 45,937 occurrences. Generated codes are explicitly distinguished from original activity labels.

Audited static exports: dashboard uses no PNG inputs; optional future Day 2 figures go into reports/figures with --no-figures support. Historical reports/data preserved. Final full suite: 82 passed, zero failed, one optional PM4Py warning in 154.97 s; pip check passed. Actual headless Edge verified main/all counts, zoom/pan, selection, no overlapping full-graph node boxes in the checked state, no app exceptions and no 390px mobile page overflow. Screenshots inspected. Native Graphviz prototype failed browser update checks and was replaced; an unrelated date-widget cleanup was reverted after regression tests. No new dependencies.

See [PROCESS_MAP_UI_VERIFICATION.md](PROCESS_MAP_UI_VERIFICATION.md) for evidence, timings, changed files and remaining dense-edge/browser limitations. No Day 6 or machine learning started. Stop here pending user approval.


## Day 6: completed and verified

User authorized the professional Process Intelligence Workspace redesign, performance investigation and ML problem definition. Retained native ECharts SVG; default horizontal Main Process, complete Detailed Process, observed boundary colors, mobile vertical arrangement, clearer selected activity details and reproducible process insights. All underlying counts retained (10,500 cases, 56,437 events, 17 activities, 39 relationships, 45,937 consecutive pairs). Browser-discovered horizontal overlap/clipping and hover fading were corrected. No new dependencies/CSS hacks or PNG dashboard inputs. Historical reports/data preserved.

Added Performance Investigation to the existing navigation, with cached reusable calculations, live Plotly charts and exports. Real candidates: duration mean 11.526/median 7.330/p95 29.205 days; 1,019 repeating cases; 99 variants with 77 rare (<10-case) variants covering 166 cases. Selected longer observed span, not actual completion/active processing time. Formula: y=1[observed elapsed days >11.105428240740741], frozen from training-only p75 after endpoint overlap purging. Prediction point: second recorded event, after investigation found first-event resource/role constant and limited activity variation. Eligible 10,366; positive 3,085 (29.761%), negative 7,281. Of these 333 already exceed the threshold at prediction time and are separated from 10,033 not-yet-known labels. Singleton traces (134) do not reach the landmark.

Chronological boundaries: validation 2018-06-27T09:27:50Z, test 2018-10-12T13:06:56Z. Train 5,951, validation 1,821, test 2,074, purged overlap 520. Final trace attributes excluded because as-of availability cannot be verified. Prefix-only event/history/time features; no future counts/variants/outcomes, no fitted transformations/model. Purging/censoring/calendar/selection limits and cautious human-review/simulation connections documented.

Verification: initial invocation 82 passed (tests overlapped early edits); final full suite **91 passed, zero failed, one optional PM4Py warning in 103.68 s**. Final focused map/mining/performance suite **37 passed in 70.08 s**. pip check: no broken requirements. Actual Edge verified both pages, exact full transition frequencies, Main/Detailed/activity controls, zoom/pan, filter/reset/empty state and no rendered exceptions; simulated mobile document/viewport both 390px. Screenshots inspected. Existing widget default/session-state log warning on reset remains disclosed; no warning suppression.

Measured local load 2.028 s, existing analysis 0.463 s, investigation 1.537 s, target design 0.502 s; final browser graph ready 2.386 s. New bounded caches and array-based prefix aggregation reduce unnecessary repeated work; local timings are not production guarantees. Small reproducible CSV/JSON artifacts only, plus explicit QA screenshots.

Created/updated modules, scripts, tests and reports listed in [DAY6_UI_VERIFICATION.md](DAY6_UI_VERIFICATION.md); research details and class balance in [DAY6_ML_PROBLEM_DEFINITION.md](DAY6_ML_PROBLEM_DEFINITION.md). Day 6 acceptance criteria met. No Day 7, ML model training, LLM, recommendation engine or simulation started. Stop pending approval.
## Combined Days 7–8: completed and verified (20 October 2026)

Implemented the reusable Event-2 feature module, explicit-threshold labels, eligibility assessment, canonical tie handling, chronological splitting via validated Day 6 logic, overlap purging, schema/leakage checks, training-only preprocessing specification and safe unknown-category transformation. Added the reproducible preparation CLI, 23 synthetic/integration tests and read-only ML Preparation dashboard section. No classifier or later-stage functionality was implemented.

Day 6 reconciles exactly: 10,500 original cases − 134 singletons = 10,366 reachable snapshots. These include 333 known positives. Of 520 overlap-purged cases, 23 are also known positives; the other 497 are additional exclusions. Final unresolved ML-ready cohort: **9,536**. Mutually exclusive accounting: 134 + 333 + 497 + 9,536 = 10,500. Threshold remains **11.105428240740741 days**, linear-interpolated p75 of 5,951 mature training outcomes before threshold-dependent known-positive removal. It was already training-only on Day 6; descriptive global p75 was never substituted.

Final partitions (cases / positive / negative): train **5,783 / 1,320 / 4,463**; validation **1,752 / 496 / 1,256**; test **2,001 / 668 / 1,333**. Retained reproducible Day 6 60/20/20 boundaries with equal timestamp grouping. Outcomes crossing the next boundary are purged. Primary features: first/second activities, prefix elapsed hours, UTC month/weekday/hour. Resource/role are preserved only in the separate audit and remain sensitivity-only until availability at ingestion is verified. Final trace attributes, future history, IDs, absolute timestamps, labels and partition metadata are forbidden predictors.

Verification: baseline **91 passed**, one optional PM4Py warning, **211.12 s**, before edits. New focused suite **23 passed in 18.05 s**. Final full `python -m pytest -q`: **114 passed**, no failures, one existing optional PM4Py accelerator warning, **199.93 s**. `python -m pip check`: no broken requirements. Actual pipeline executed twice; both Parquets, CSV and JSON read back, accounting/schema/leakage checks passed, source XES/cleaned Parquet hashes unchanged. Repeated dataset rows are stable. Preparation measured **6.289 s**, total **7.241 s** initially; warm **1.407 s**, total **2.488 s** (interpreter import excluded). Dataset **367,788 bytes**, all-case audit **618,707 bytes**; approximately 1.05 GB free before temporary browser cleanup. Exact measurements and hashes are in `outputs/reports/day7_8_runtime.json`.

Actual headless Edge browser verification passed: ML metrics 9,536 / 11.105428240741 / 333 and three tables; explicit no-trained-model message; existing Overview, Process Mining SVG, Performance Investigation, activities/resources, variants/repetition, boundaries and case explorer all rendered; **zero rendered exceptions**. Simulated mobile document and viewport both **390px**. Desktop/mobile screenshots inspected directly. ML navigation measured **1.130 s**. Evidence: `outputs/reports/browser_checks/day7_8/verification.json`, `ml_desktop.png`, `ml_mobile.png`. Initial sandboxed Edge startup/debugging connections failed; launching the dedicated hidden browser outside the sandbox succeeded. No browser failure is being presented as a successful check.

See [DAY7_8_ML_PREPARATION.md](DAY7_8_ML_PREPARATION.md) for the full artifact inventory, methodology and limitations. Remaining concerns: observed endpoints cannot certify actual completion or prompt label ingestion; unknown censoring, source-order ties, singleton and endpoint-purging selection, historical research-design inspection of holdouts, and unverified resource/role availability. No causal optimization benefit or predictive performance claimed. Next step after approval: timing/prevalence baselines and an interpretable classifier with train-only fitting and validation-based selection. Days 7–8 stop here; no final classifier, recommendation engine, simulation, LLM or agent trained/implemented.

## Full application QA before Day 9: completed (20 October 2026)

Verified all eight existing pages and independently checked the raw XES against cleaned case/activity/time rows. Counter/Pandas calculations reproduce 10,500 cases, 56,437 events, 17 activities, 99 variants, 39 relationships and 45,937 occurrences. Independently reconstructed every ML row/label/split and train-only preprocessing statistic; 9,536 rows, partitions 5,783/1,752/2,001 and threshold 11.105428240740741 days match. Original dataset fingerprints remain unchanged.

Fixed the reproducible duplicate-default/session-state warning on filter reset by initializing widget state once without competing defaults. Added date/duration help and clarified that Performance Investigation's 10,366 Event-2 snapshots differ from the final unresolved dataset; resource/role remain sensitivity-only. Added two regression tests. Baseline: 114 passed / one optional PM4Py warning / 173.78 s. Final full suite: **116 passed / one optional PM4Py warning / 164.16 s**. Final pip check: no broken requirements. Intermediate stale-label/test-selector failures were corrected; see the UAT report.

Actual Edge main and supplemental browser suites passed, including every page at desktop/simulated-mobile widths, filter/reset/calendar/duration interactions, refresh, activity/case/variant selectors, Main/Detailed exact counts, wheel zoom/drag pan, graph visibility/labels/focus, empty variant comparisons, mobile sidebar navigation and CSV downloads/read-back. Zero rendered exceptions; main suite captured no browser-console errors. Mobile document and viewport both 390px on all eight pages. Screenshots inspected. Intermediate automation timing/selector/context issues were resolved and disclosed in the report.

Created `docs/SMARTBPM_USER_TESTING_GUIDE.md` with every-page instructions and a full real-case walkthrough for declaration 108210 (18 events, 11 activities, 33.81275463 observed days). Created `docs/SMARTBPM_UAT_REPORT.md`, independent audit and browser helpers/results; README links both guides. Evidence is in `outputs/reports/uat_data_audit.json` and `outputs/reports/browser_checks/uat/`. Temporary QA browser profile removed after checks; Streamlit remains at http://localhost:8504.

Ready for the next authorized thesis development step with documented limits: censoring/completion uncertainty, event arrival-time uncertainty, source-order ties, selection/purging bias, dense graph navigation and single-browser/simulated-mobile coverage. No guarantee of zero defects or production readiness. No classifier trained, recommendations/simulation added, or Day 9 work begun. Stop here awaiting the user's next instruction.

