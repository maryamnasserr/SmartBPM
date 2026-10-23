# Day 6 UI verification

## Scope and investigation

The requested workspace redesign and performance investigation are implemented inside the existing Streamlit app, with no new dependencies or separate app. The original graph was already interactive ECharts SVG. Its top-to-bottom default, tall canvas, fixed large nodes and uncollapsed explanations/isolated inventory created a narrow reading path and pushed inspection far down the page. The full graph is genuinely complex; rendering is only part of the issue. Display-only edge thresholds were already scientifically sound and remain so.

Reviewed app.py, ui_mining.py, process_map_data.py, process_mining_charts.py, dashboard/filter/cache functions, process discovery, existing methodology/verification documents and tests. The baseline test invocation returned 82 passed, one optional PM4Py warning, 215.59 s. It began before edits; some later UI checks overlapped implementation, so it is not an immutable checkout benchmark. Final regression results below are the acceptance evidence.

## Interface and renderer

Process Intelligence Workspace provides the existing bordered cohort/discovery KPIs, a horizontal primary graph, activity inspection and reproducible process insights. Main Process emphasizes seven high-frequency relationships; Detailed Process reveals every observed relationship. Direction, frequency/edge/focus controls, optional counts and an activity selector remain functional. Main threshold controls are disabled in the all-relationship mode so Detailed Process genuinely shows all edges. Zoom/pan and alternative direction provide complexity management there.

Retained native Streamlit ECharts rather than adding or replacing a compatible renderer. Deterministic ranking remains a layout aid only; loops/branches and all selected edges remain. Horizontal spacing, smaller detailed-view boxes, a shorter 460px horizontal canvas and mode-specific zoom reduce overlap. Main view contains all six connected activity boxes without clipping in the checked desktop state. ECharts media configuration rearranges positions vertically on narrow screens. Normal hover no longer fades unrelated labels into near invisibility. No custom CSS or frontend modifications.

Readable action/role labels preserve exact activity strings in tooltips/details. Blue indicates an observed start, green an observed end, teal the selected activity; starts/ends can also occur internally and are not formal completion semantics. Codes such as A15 are generated display identifiers, not source activity codes. The original exact label is retained. Selection uses the synchronized selector, not graph-node callbacks.

Activity details include event/case/repeated-case counts, starts/ends, singleton counts, preceding/following frequency tables and median observed gap hours. Process insights report the leading route and most commonly repeated labels from existing analytical tables. Variant/repetition tabs and exact CSV exports remain available. Longer-case and unusual-variant evidence is explored in Performance Investigation.

## Visibility, isolation and interpretation

Full cohort: 10,500 cases, 56,437 events, 17 activities, 39 relationships, 45,937 consecutive pairs and 99 variants. Default Main Process: seven relationships, six connected activities, 40,554 occurrences, 32 hidden relationships. Eleven activities without visible edges remain explicitly listed in a collapsed inventory and inspectable; an inspected disconnected activity has a dashed box. No activity is isolated in the full graph. SAVED has 135 occurrences, 134 singleton cases and one full outgoing relationship. Display controls never recalculate frequencies or create bridges. Sidebar filters select whole cases and therefore can change the analytical graph legitimately.

Nodes are activities; arrows mean consecutive recorded events in a case; frequency counts pairs including repeats. A simplified frequent-edge summary is not a complete case variant. No BPMN gateways/concurrency invented. Repetition and long elapsed time are not automatically defects; frequency does not establish causal bottlenecks. All gaps/durations are observed elapsed time, not service or queue time.

## Performance Investigation integration

The seventh navigation page uses reusable performance.py calculations and cached results, with interactive Plotly duration, repetition and variant charts, threshold tables, per-variant repetition counts, prediction-point comparison, candidate comparison and CSV exports. Historical tables follow the selected complete-case cohort. The research target/threshold/splits explicitly remain anchored to the full dataset. No model prediction, accuracy or claimed improvement is displayed.

The final proposal predicts recorded span >11.105428240740741 days after the second event: 10,366 eligible cases, 3,085 positives, 134 singleton exclusions, and 333 already-above-threshold prefixes reported separately. The ML definition document and JSON contain leakage rules, train-only threshold provenance and temporal purging.

## Automated checks

- `python -B -m pytest -q`: **91 passed, zero failed**, one optional PM4Py importer accelerator warning, **103.68 seconds**.
- Earlier full run during implementation: 89 passed in 121.77 s; the two added regressions check second-prefix future-event invariance and equal-time partition grouping.
- `python -B -m pip check`: **No broken requirements found**.
- Final chart emphasis/text-only refinement is followed by focused mining/map/performance regression execution; result recorded below.

Tests cover existing Day 1-5 analytics and fingerprints, DFG count conservation, readable/original labels, visibility/isolation, selected counts, duration boundaries, invalid/null fields, canonical ordering, prefix eligibility, future-attribute mutation, train-only threshold stability under changed holdout labels, split overlap purging, class balance, filtering/empty/reset behavior and exact table exports.

## Browser verification

Actual dedicated headless Microsoft Edge opened the running app through local CDP. `scripts/verify_day6_browser.py` exercises Main/Detailed modes, all frequencies against the saved validated transition table, activity selection, real wheel zoom/drag pan, filter/reset controls, empty state, research-page navigation and 390px mobile sizing. Live ECharts data, rather than a screenshot alone, is inspected. Screenshots under outputs/reports/browser_checks/day6 are verification evidence; they were opened for visual inspection. Latest results are recorded in verification.json and summarized below.

During development actual browser bounding-box checks caught small horizontal node overlaps in the detailed graph. Detailed-box widths were reduced and checked again. The main view initially clipped endpoints with full-graph zoom, so main/full zoom settings were separated. A verification-helper selector assumed role=slider, whereas this installed Streamlit uses input[type=range]; the helper was corrected. No application warning was suppressed.

## Performance and dependency behavior

Latest reproducible single local run in day6_investigation.json: data loading 2.028 s; existing descriptive analysis 0.463 s; candidate/prediction-point investigation 1.537 s; target/split design 0.502 s. Initial prefix tuple aggregation took about 4.958 s for investigation and 2.198 s for target design in an earlier run. Reused the existing array/group-position approach, yielding later samples around 1.09-1.54 s and 0.39-0.50 s. This is local observational evidence under varying load, not a controlled production speedup. Loading/import/startup and browser rendering are distinct from compute timings. Existing cache bounds remain; new bounded caches avoid repeating investigation on unchanged cohorts.

Disk inspected before output generation (initial headroom about 43 MB; later about 228 MB). Only small summaries and browser evidence are added; no duplicate full dataset, model artifacts or dependencies. Raw XES/processed Parquet and historical reports remain intact; fingerprint integration tests pass.

## PNG audit

Only the explicit Day 2 save_charts workflow writes research PNGs, now under reports/figures with --no-figures available. No st.image or PNG chart input is used in the app. Dashboard charts are live ECharts/Plotly. Historical PNGs were not deleted. Browser screenshots are generated explicitly by QA helpers, not during routine use.

## Remaining limitations and warnings

Detailed graph still has crossing arrows; optional frequency labels can clutter it. Pan/zoom, direction/focus or Main Process is needed on smaller screens. Mobile reorientation does not infer new edges. Native ECharts does not provide node-selection callbacks here, so inspection uses the selector. Browser coverage is Edge and simulated 390px mobile, not all physical devices/browsers.

PM4Py emits an optional r4pm import-acceleration warning while testing raw XES; Parquet dashboard loading works without it. Reset can log Streamlit's existing duplicate-default/session-state widget warning because explicit defaults restore browser values. This was investigated as the established reset contract; browser filter/reset/empty checks and tests pass. It is retained and disclosed rather than suppressing it or repeating the prior date-widget regression.

Unknown censoring, early feature availability, sparse variants, calendar drift and purged-case selection bias constrain the ML proposal. No trained model or causal recommendation/simulation exists. Day 7 is not started.

## Final acceptance evidence

Final focused execution after the emphasis/text refinement: `python -B -m pytest -q tests/test_process_map_ui.py tests/test_process_mining.py tests/test_performance.py`: **37 passed, zero failed in 70.08 s**.

Final actual Edge run passed: main 7 links; detailed 39 links/17 nodes; every displayed frequency exactly matched day5_transitions.csv; no overlapping detailed node boxes in the checked desktop state; wheel zoom and drag pan worked; Saved inspection showed 135 occurrences and 134 singleton cases. Performance page showed the final second-event design and actual historical KPIs. Actual sidebar slider changes altered counts; Reset restored 10,500; setting the lower duration bound to 470 days produced a safe empty state; reset restored the page again. No rendered exceptions in normal, research or empty views. Both graph and performance pages had 390px document width at a 390px viewport. Final first-graph readiness was 2.386 s (navigation-to-ready, workstation-specific). Desktop map/research and mobile screenshots were opened and inspected.

## Files created or modified

Created src/smartbpm/performance.py, src/smartbpm/ui_performance.py, scripts/run_day6.py, scripts/verify_day6_browser.py, tests/test_performance.py, docs/DAY6_ML_PROBLEM_DEFINITION.md and this document. Updated app.py, src/smartbpm/ui_mining.py, src/smartbpm/process_mining_charts.py, tests/test_process_map_ui.py, README.md, PROCESS_MINING_METHODOLOGY.md and DEVELOPMENT_PROGRESS.md. Small artifacts: day6_candidate_targets.csv, day6_target_definition.json, day6_investigation.json and browser_checks/day6 verification JSON/screenshots. Historical verification script and earlier reports remain preserved.

Day 6 acceptance criteria met for this local prototype. No model, LLM, recommendation engine or simulation was trained/implemented. Recommended Day 7: review the observational target and eligibility, confirm event-attribute availability, lock splits/features and implement interpretable baselines with leakage tests, known-positive separation and censoring/endpoint sensitivity. Day 7 awaits explicit approval.

The final updated application was launched on http://localhost:8501 and its health endpoint returned HTTP 200. Browser QA used an isolated instance on port 8502. Temporary QA browser profile and port-8502 server were cleaned up; port 8501 remains available.
