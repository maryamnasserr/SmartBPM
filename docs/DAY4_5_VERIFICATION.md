# Combined Days 4–5 verification

Verified on 2026-10-20 (Africa/Cairo). Scope: application quality, measured performance improvements and observed process mining. No ML, recommendation generation, simulation, LLMs or agents implemented.

## Features and files

- Improved the existing app with native bordered KPI cards and metric help, active-filter context, shortened readable activity ticks (full names remain on hover), inspectable frequency tables and actionable empty states. Removed injected styling in favor of native Streamlit components and the existing theme.
- Added Process Mining to the existing five views and shared whole-case cohort filters. Includes a directed, zoomable Plotly DFG with frequency/focus/edge-limit controls, an activity-code legend, coverage counts, exact edge statistics and exports. All cohort transition statistics remain inspectable even when display controls hide edges.
- Added exact variant duration summaries/selection/comparisons, repeated approval/rejection-label subsets and repetition-duration comparisons. No causal claims or invented service/queue times.
- Optimized sequence extraction without changing analytical values; builds only charts needed by the current page. Existing bounded load/cohort/analysis caches remain; added bounded discovery caching.

Created: src/smartbpm/process_mining.py, process_mining_charts.py, ui_mining.py; tests/test_process_mining.py; scripts/benchmark_dashboard.py and verify_day4_5_browser.py; docs/PROCESS_MINING_METHODOLOGY.md and this report.

Modified: app.py; src/smartbpm/dashboard.py, dashboard_charts.py, exploration.py; README.md; docs/DEVELOPMENT_PROGRESS.md. No dependencies added or changed.

New small analytical artifacts: outputs/reports/day5_transitions.csv, day5_variant_performance.csv, day5_repetition_groups.csv, day5_mining_summary.json. Measurements: day4_5_performance_baseline.json, day4_5_performance_after.json, day4_5_runtime_benchmark.json. Browser evidence: day4_5_browser_verification.json and day4_5_{desktop,activities,variants,process_map,mobile}.png. Screenshots are verification artifacts, never chart inputs. Earlier outputs and original/processed datasets remain preserved.

## Defects found and fixes

1. Variant extraction spent most of its time creating thousands of small Arrow-backed Pandas groups. Replaced per-case Series aggregation with array indexing using group positions; serialize unique variant labels rather than every case. All nine Day 2 tables and key summary fields matched the saved artifacts.
2. Each page constructed eight figures while normally displaying two. Added requested-chart construction; the public default still creates all eight for compatibility.
3. Reusable duration filtering silently accepted NaN/infinite bounds. Added finite-value validation and known-answer regression cases. Date filtering now compares vectorized UTC timestamp bounds instead of allocating Python date objects.
4. Real-browser reset cleared Python state but left the native slider's prior value in the browser. Navigating resubmitted that stale value, returning from 10,500 to 10,328 cases. Replaced key deletion with explicit callback assignment of all filter defaults. Browser verification now checks slider state, stable totals after navigation and downloaded CSV contents; all passed after the fix. AppTest alone had not exposed this frontend state issue.
5. Download buttons now avoid unnecessary reruns via on_click="ignore". Variant inspection/comparison state is reconciled when a new cohort removes old variant IDs.

Verification helper development also required DOM readiness waits and selection of the actual app tab rather than Edge's download hub. These were browser-script issues; the CSV mismatch above exposed the real reset defect. No warnings were suppressed.

## Actual dataset findings

| Measure | Observed result |
| --- | ---: |
| Cases / events / activities | 10,500 / 56,437 / 17 |
| Exact variants | 99 |
| Distinct directly-follows edges | 39 |
| Consecutive event-pair occurrences | 45,937 = 56,437 − 10,500 |
| Median case elapsed days | 7.330 |
| Cases repeating activities | 1,019 |
| Cases repeating approval labels | 276 |
| Cases repeating rejection labels | 150 |
| Median days, repeated activity | 13.249 |
| Median days, no repeated activity | 7.227 |

Approval/rejection subsets overlap. Duration differences are associations; case mix, routes and observation limits can confound comparisons.

Most frequent edge: supervisor final approval -> Request Payment, 10,038 occurrences, median gap 27.43 h, p95 265.30 h. Request Payment -> Payment Handled: 10,037 occurrences, median gap 77.77 h, p95 146.33 h. These are elapsed gaps between consecutive recorded timestamps; service and queue time cannot be separated.

Leading variant: 4,618 cases (43.98%), median observed duration 7.036 days; second variant: 2,473 cases (23.55%), median 10.233 days. Variant rank/ID is cohort-specific. Ten tied-timestamp cases retain original source-order tie-breaking; causal order remains unknown.

## Performance measurements

Local perf_counter timings; three samples per compute operation. Imports/startup excluded from compute timings. Concurrent verification and system load can affect samples. No production latency guarantee is claimed.

| Operation | Baseline median | After median |
| --- | ---: | ---: |
| Full analytical preparation | 4.084 s | 0.464 s |
| 1–20 day cohort analysis | 3.887 s | 0.442 s |
| Ordinary Overview chart construction | 1.242 s (all eight built) | 0.183 s (only two needed) |
| Load and validate Parquet | 4.109 s | 2.187 s |
| Duration-only filtering | 0.427 s | 0.280 s |

Loading logic was not optimized; its difference reflects run/system variability and should not be claimed as a code improvement. Duration-only filter variability likewise is not isolated proof of an optimization (the date-bound change is not exercised by that measurement). The sequence and lazy-chart changes are the measured significant implementation improvements. Producing all eight figures still took about 1.068 s after changes; fewer requested figures explains the page-render reduction.

New operations: DFG/gap calculation median 0.411 s; default 20-edge interactive map median 0.133 s (first figure creation 0.930 s).

Actual Streamlit AppTest: initial run 8.167 s; median unchanged cached rerun 0.877 s. First 1–20 day cohort selection 2.767 s, return to full 0.803 s, repeat selection 1.261 s. These include Streamlit execution but exclude browser/network rendering. Cache memory is bounded; first loads and newly selected cohorts still incur validation/analysis costs.

## Commands and tests

Commands executed from C:\Users\Maryam Nasser\Desktop\SmartBPM with the .venv Python 3.12 interpreter. Verification processes set PYTHONDONTWRITEBYTECODE=1 to reduce disk writes.

- python -B -m pytest -q: baseline 53 passed, 1 optional PM4Py warning, 149.91 s.
- Day 4 focused tests: 12 passed in 37.83 s; full numerical comparison against the saved Day 2 summaries and nine tables passed.
- python -B -m pytest -q tests/test_process_mining.py: 19 passed in 40.98 s.
- Full combined suite before the browser-discovered reset fix: 72 passed, 1 warning in 142.21 s.
- After reset/readability refinements, dashboard/mining tests: 30 passed in 68.12 s.
- Final full-suite result after all fixes: **72 passed, 0 failed, 1 optional PM4Py warning in 116.95 s**. Dependency check: **No broken requirements found**.
- python -B scripts/benchmark_dashboard.py: generated the measured runtime report; AppTest emitted its bare-mode ScriptRunContext setup warning, with all timed app runs free of exceptions.
- python -B scripts/verify_day4_5_browser.py: final real-browser checks passed, including actual downloaded CSV comparison.
- python -B -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --server.fileWatcherType none: application started and served HTTP 200 /_stcore/health. Restarted the owned verification server after module changes to ensure the browser used current code.

Tests use independent small-log oracles for edges/gaps, timestamp ties, self-loops, singleton/empty logs, case boundaries, no false path bridging, variants/durations, repeated labels, invalid inputs, exact exports and lazy charts. Real integration tests check original counts, historical equivalence, cohort consistency and process-map state. Original raw/Parquet fingerprints are checked against Day 2.

## Browser results

Dedicated headless Microsoft Edge; actual served application, not only Streamlit AppTest. Inspected desktop, activity, process-map and mobile screenshots.

- All six navigation views render; full totals 10,500 / 56,437 / 17, median 7.33 days.
- Plotly pointer zoom changed an axis range; activity chart has 17 bars.
- Duration slider selected 10,328 cases/56,190 events, median 7.35 days; reset restored 10,500 cases and persisted through navigation.
- Case inspection visible. Downloaded 10,500-case CSV matched the saved case table exactly.
- Mining metrics 45,937 occurrences, 39 relationships, 99 variants; map has 17 nodes and 20 displayed edges by default.
- Frequency threshold produced a safe no-edge state while preserving all 10,500 cohort cases. Lowering the threshold restored the map.
- Downloaded displayed-edge CSV (20 rows) and full-transition CSV (39 rows) matched analytical results exactly. Temporary downloaded copies removed after checks.
- Mining variant/repetition tabs opened. Simulated mobile viewport/document widths both 390px; no horizontal page overflow. Zero rendered application exceptions.

## Interpretation, warnings and limits

Definitions, formulas, source assumptions and per-metric limitations are in PROCESS_MINING_METHODOLOGY.md, with primary PM4Py references. The DFG is observational adjacency, not a formal BPMN/control-flow model. No gateways, concurrency semantics or causal bottlenecks inferred. Low-sample gap percentiles can be unstable. Repetition is not automatically unnecessary work. Elapsed times are not independently measured active processing or queue waiting times. Observation boundaries and timestamp ties limit interpretation.

Dense maps may require zoom, fewer edges, focus or disabling count labels; exact labels remain in the legend and hover. Browser checks cover desktop Edge and a simulated mobile viewport, not all browsers or physical devices. Disk space remains limited; no new dependencies or large duplicate datasets were generated. Existing optional PM4Py r4pm importer warning remains; XES import works and ordinary UI exploration reads only Parquet. No warning suppression added.

Acceptance criteria met: application launches; original functionality preserved; interface visibly improved; real-data process mining integrated; cohort and map controls verified; all tests pass; actual browser/export checks pass; measurements and limits documented. Raw and processed fingerprints match Day 2. Dedicated browser profile and temporary downloads were removed; about 68.7 MB remained free. The app remains available at http://localhost:8501 at handoff.

Launch from the activated environment with `python -m streamlit run app.py`. Stop after these combined days; Day 6 and later features require explicit approval.

