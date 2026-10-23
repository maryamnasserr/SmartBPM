# SmartBPM

Bachelor thesis prototype: Designing an AI-Augmented Business Process Management Platform.

**Days 11–12:** Predictive Analytics now compares six models, including random forest and gradient boosting, with training-only temporal optimization, grouped global/local explanations and downloadable analytical evidence. The selected forest has validation AP .483776; the test set remains locked. See [advanced ML/XAI results and walkthrough](docs/DAY11_12_ADVANCED_ML_XAI.md). No LLM, recommendations or simulation have been implemented.

Run the existing saved models with `.\.venv\Scripts\python.exe -m streamlit run app.py`. Reproduce the advanced artifacts with `.\.venv\Scripts\python.exe scripts/run_day11_12.py`, then independently verify them with `.\.venv\Scripts\python.exe scripts/verify_advanced_artifacts.py`.

**Days 9–10:** Predictive Analytics now provides trained prevalence/elapsed baselines, logistic regression, a constrained tree, validation metrics, calibration and case explanations. The test holdout remains locked. See [results and the interactive walkthrough](docs/DAY9_10_ML_RESULTS.md).

To learn the application and verify it yourself, start with the [beginner-friendly user testing guide](docs/SMARTBPM_USER_TESTING_GUIDE.md). The [full application UAT report](docs/SMARTBPM_UAT_REPORT.md) records independent data checks, fixes, automated/browser coverage and limitations before Day 9.

The intended architecture is historical event log -> validation -> process mining -> predictive ML -> evidence-based recommendations -> human review -> baseline/scenario simulation -> KPI dashboard. Days 1 and 2 implement loading, validation, reproducible preprocessing and descriptive exploration. Findings, predictions and hypothetical scenario results must remain distinguishable.

Use Python 3.12 on Windows PowerShell. Run these commands from `C:\Users\Maryam Nasser\Desktop\SmartBPM`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/inspect_dataset.py
.\.venv\Scripts\python.exe -m pytest -q
```

The interpreter can be called directly; environment activation is optional. The requirements file records exact resolved dependencies for the verified project environment.

Place the original XES file at `data/raw/DomesticDeclarations.xes`. Raw data, processed data, environments and secrets are excluded from Git. Keep the original dataset unchanged. The inspection report includes a SHA-256 fingerprint for reproducibility.

`src/smartbpm/dataset.py` provides reusable PM4Py loading, required-field validation and schema profiling. `scripts/inspect_dataset.py` is its command-line interface; default paths are anchored to the project directory. `tests/` contains isolated synthetic tests and a separately marked real-data integration test. `data/processed/` holds derived datasets, including the frozen ML partitions. `outputs/` separates reports, models and simulations. `docs/DEVELOPMENT_PROGRESS.md` tracks acceptance and limitations.

Inspection writes `outputs/reports/dataset_profile.json`, including all observed columns and types, trace and event attributes, missing-value counts, activity frequencies, UTC timestamp range and five actual records. No cases are removed or imputed. Missing required identifiers, activity names or timestamps cause validation to fail. Absent optional attributes are reported. Elapsed time between events must not be interpreted as processing duration.

For only isolated tests use `python -m pytest -q -m "not integration"` with the virtual environment interpreter. The integration test skips when the local dataset is absent and does not hard-code published dataset counts.

Current scope: Days 1–12, including historical process mining, predictive validation and explainable AI. Further development requires explicit approval. Recommendations, LLM integration, simulation and agents remain pending. Earlier sections below record historical development stages.


## Day 2: reproducible quality checks and exploration

From `C:\Users\Maryam Nasser\Desktop\SmartBPM`, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/run_day2.py
.\.venv\Scripts\python.exe -m pytest -q
```

The CLI defaults are anchored to the repository, so it also works from another directory when invoked by absolute path. Optional flags: `--dataset`, `--processed-dir`, `--report-dir`. Default outputs are separate from the source dataset; output directories containing the raw source are rejected.

Module interfaces:

- `load_event_log(path, validate=True)` returns the original PM4Py log and flattened DataFrame. Day 1 remains strict by default; Day 2 uses `validate=False` to save diagnostic findings before rejecting invalid analytical inputs.
- `quality_report(frame, columns=Columns())` returns schema, null/type/required-field checks, duplicate-record and duplicate-ID counts, timestamp chronology, case-attribute consistency, trace lengths, repetitions and activity/resource frequencies.
- `preprocess_events(frame, columns=Columns())` returns `(ordered_events, transformation_report)`. Explicit mappings default to `case:concept:name`, `concept:name`, `time:timestamp`, `id`, `org:resource`. Override the `Columns` dataclass in Python for other names. Type expectations remain specific to this dataset.
- `describe_process(ordered_events, columns=Columns())` returns `(summary, tables)` for ordered UTC events.
- `run_day2(source, processed_dir, report_dir, columns=Columns())` orchestrates the XES audit, validation, Parquet round trip, tables and charts; returns the quality, preprocessing and EDA reports.

The workflow audits original XES date offsets before PM4Py normalization. Naive/invalid timestamps, invalid required fields, invalid dataset types, conflicting case attributes, duplicate trace identifiers or empty traces stop preprocessing. Duplicate records and event IDs are reported separately and retained for provenance review. Timestamp ties retain original source order. `_source_order` records each event's original zero-based flattened XES position. No records are deleted, deduplicated or imputed.

PyArrow is the only dependency added on Day 2, for Parquet support; Matplotlib was already available. Exact versions remain in `requirements.txt`.

Outputs:

- `data/processed/domestic_declarations_cleaned.parquet`: all 56,437 events, all ten original columns plus `_source_order`, timestamps in UTC, deterministic ordering.
- `outputs/reports/data_quality_report.json`, `preprocessing_report.json`, `initial_eda_summary.json`.
- Nine CSV tables: case summaries, activity/resource frequencies, full variants, repeated activities per case and per activity, starts, ends and duration statistics.
- Seven PNG charts: activity/resource frequencies, starts, ends, duration distribution, trace lengths and top variants.
- `docs/DAY2_METHODOLOGY.md`: observed findings, interpretation and artifact guide.

Read `case_summary.csv` for each case's start/end timestamps, elapsed days, event count, variant ID, repetitions and descriptive review flags. IQR flags identify unusual trace lengths; they are not exclusion rules. Payment endpoint flags do not establish whether a case is complete. Variant sequences are JSON arrays in CSV cells, which preserve exact activity names.

Case elapsed duration is not active processing time. Resource values represent broad labels, not identifiable workers. UTC offsets alone do not establish a named timezone. No SLA, case outcome, processing duration, causal mechanism or capacity is inferred. Undefined statistics for tiny logs are written as JSON `null`. The original XES checksum and Parquet round trip are verified on each successful run.


## Day 3: interactive web application

From `C:\Users\Maryam Nasser\Desktop\SmartBPM`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501 (or the URL Streamlit prints). If activation is blocked, run `.\.venv\Scripts\python.exe -m streamlit run app.py` directly.

The application reads the real processed Parquet dataset and generates interactive Plotly figures; saved PNG charts are not used. Overview, activities/resources, variants/repetition, case boundaries and case inspection are available through sidebar navigation. Selected-cohort metrics are separate from full-dataset totals.

Filters select whole cases by activity/resource presence, inclusive UTC case-start dates and observed elapsed duration, retaining complete histories. Empty activity/resource selections show no matching cases; Reset filters restores the full dataset. Activity/resource matches may be on different events within a case. Duration is elapsed observed time, not active processing time.

See [Day 3 application guide](docs/DAY3_APPLICATION.md) for filter semantics, architecture, cache behavior, testing and limitations. Run all tests with `.\.venv\Scripts\python.exe -m pytest -q`.


## Days 4–5: process intelligence and process mining

Launch command is unchanged: `python -m streamlit run app.py` in the activated project environment. The five existing views remain, with **Process Mining** added to the same sidebar and case-cohort filters.

The improved interface uses native bordered KPI cards with metric help, visible active-filter context, readable activity labels and inspectable frequency tables. Chart hover/export data retain full activity names. Reset explicitly restores both server and browser widget values. Plotly constructs only the charts needed by the current view. Variant extraction avoids building thousands of small Pandas groups, with numerical equivalence checked against saved Day 2 tables.

Process Mining includes a directed, zoomable PM4Py frequency DFG; minimum-frequency/edge-count/focus controls; transition occurrence and distinct-case counts; observed gap-hour statistics; complete variant duration summaries and comparisons; repeated approval/rejection label groups; and matching CSV exports. Hiding map edges never removes events or creates artificial adjacency. Observed gaps do not separately measure service or queue waiting time. Repetition-duration differences are associations, not causal effects.

See [verification report](docs/DAY4_5_VERIFICATION.md) and [metric definitions and methodology](docs/PROCESS_MINING_METHODOLOGY.md). All prior data and validated outputs are preserved. No dependencies were added.

```powershell
# From C:\Users\Maryam Nasser\Desktop\SmartBPM
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/benchmark_dashboard.py
.\.venv\Scripts\python.exe -m pip check
```

The optional benchmark records compute times and real Streamlit AppTest reruns in `outputs/reports/day4_5_runtime_benchmark.json`. Browser verification scripts require a dedicated local Edge CDP session; they are verification helpers, not application dependencies or launch requirements.


## Process map readability update

Process Mining now uses native interactive ECharts SVG with readable activity names, a seven-edge main-path default, all-transition mode, zoom/pan and linked activity inspection. Other analytical charts remain Plotly. Graph controls hide relationships without changing cohort counts. Hidden activities are explained explicitly. See [UI verification](docs/PROCESS_MAP_UI_VERIFICATION.md). Launch remains `python -m streamlit run app.py`. Future optional Day 2 PNG exports go under `outputs/reports/figures/`; `scripts/run_day2.py --no-figures` skips them. Historical figures remain preserved.


## Day 6: process intelligence and ML problem definition

Process Mining now opens a balanced left-to-right Main Process view, with Detailed Process, activity details, observed endpoint colors and reproducible process insights. Small screens use a vertical graph arrangement; zoom/pan and the linked activity selector remain available. Performance Investigation adds duration thresholds, repetition associations, rare/common variant comparisons and an explicitly proposed ML design. Sidebar filters update historical findings; the full-dataset target definition remains frozen and clearly labeled. No model is trained.

The proposed target is observed case span greater than 11.105428240740741 days, immediately after the second event. This training-only research threshold is not an SLA. There are 10,366 eligible cases; 333 already exceed it at the prediction point and are reported separately. See [ML problem definition](docs/DAY6_ML_PROBLEM_DEFINITION.md) and [UI verification](docs/DAY6_UI_VERIFICATION.md).

```powershell
python -m streamlit run app.py
python -B scripts/run_day6.py
python -B -m pytest -q
python -B -m pip check
```

Day 6 artifacts are small CSV/JSON summaries under outputs/reports. No duplicate analytical dataset or routine PNG exports are created. No Day 7 training, LLM, recommendation engine or simulation is implemented.
# Days 7–8 ML preparation

Run `.\.venv\Scripts\python.exe scripts/prepare_ml_dataset.py` to reproduce the unresolved Event-2 ML dataset and separate all-case outcome audit. Open **ML Preparation** in the Streamlit sidebar for frozen preparation statistics. This preparation step does not train classifiers; the Days 9–10 models/results are available separately in Predictive Analytics. See [the methodology and artifact inventory](docs/DAY7_8_ML_PREPARATION.md) for the reconciled 9,536-case cohort, training-only threshold, chronological splits, feature allowlist and limitations.

