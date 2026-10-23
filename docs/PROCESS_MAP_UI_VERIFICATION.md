# Process map UI verification

## Result and scope

Process map readability fixes are implemented. No Day 6, machine learning or new process discovery semantics were introduced. Launch with `python -m streamlit run app.py` in the project environment and choose Process Mining.

## Investigation

The previous map was an interactive Plotly graph, not a PNG. PM4Py discovers consecutive within-case event pairs after case/UTC timestamp/source-row ordering. Independent adjacency checks verify its frequencies. A force-directed NetworkX layout, small code-only nodes and count annotations made arrows and labels overlap. The old top-20-edge view kept all activities: FOR_APPROVAL by ADMINISTRATION, PRE_APPROVER and SUPERVISOR each lost their two incident relationships; SAVED by EMPLOYEE lost its one relationship. None is isolated in the full graph. The problem included incomplete explanation of visual filtering, not incorrect discovery counts.

Full data: 10,500 cases, 56,437 events, 17 activities, 99 exact variants, 39 distinct relationships and 45,937 transition occurrences (events minus nonempty cases). SAVED by EMPLOYEE occurs in 135 cases, including 134 single-event cases; its one full relationship is to Request Payment, frequency one. Single-event cases contribute no consecutive pairs.

## Implemented visualization

Native Streamlit ECharts SVG replaces the Plotly process map. Streamlit 1.66.0 already provides this API; no package was added. Readable action/role boxes preserve exact original activity strings and generated Axx identifiers in tooltips and inventory. ECharts supports wheel zoom, drag pan, reset and responsive sizing. Other analytical distributions remain Plotly.

Default main-path view shows the seven most frequent relationships: six connected activities, 40,554 of 45,937 occurrences and 32 hidden relationships. This is a frequent-edge summary, not necessarily an executable case variant. All observed transitions bypasses display thresholds and reveals all 39 relationships and 17 activities. Minimum frequency, maximum edges and activity focus only hide existing edges; sidebar filters select complete cases. Counts are never recomputed from the visually reduced graph.

Top-to-bottom is the default; left-to-right is available. Deterministic acyclic ranking constraints prioritize frequent forward edges and the dominant observed start solely for layout. Loops and every selected edge remain rendered. Equal-aspect coordinates, separate lanes and initial zoom avoid flattened or overlapping boxes. Dense full graphs extend beyond the frame and require pan/zoom. Edge labels are optional; tooltips and exact tables always retain frequencies.

Disconnected activities are explicitly listed with full/hidden relationship counts and reasons. The functional activity selector highlights its box, including a dashed isolated box when appropriate, and reports occurrences, cases, repeats, starts, ends, singleton cases and incoming/outgoing counts. Native node-click selection callbacks are unavailable; the selector is the supported inspection control.

A native Graphviz prototype was rejected during actual browser checks: zoom was disabled and an update produced a client-side layout error/stale SVG. Final implementation uses the native ECharts graph API, with no frontend patch or external component. API reference: https://docs.streamlit.io/develop/api-reference/charts/st.echarts_chart.

## Scientific interpretation

Nodes are observed activity labels; arrows are directly consecutive events in the same case; frequencies count occurrences, including repeats. Variants are exact ordered sequences. Repetition alone is not a defect. Frequencies do not establish causal bottlenecks. Observed case duration and inter-event gaps include waiting/unobserved intervals, not separately measured active processing time. Timestamp ties and incomplete observations remain limitations. Layout ranks do not imply formal gateways, concurrency or causal precedence.

## PNG audit and reproducibility

No primary dashboard visualization reads saved PNGs. Static exports originate in exploration.save_charts through the explicit Day 2 workflow. Future Day 2 figures are organized under outputs/reports/figures; --no-figures skips them. Historical root-level charts, raw XES, processed Parquet and validated reports remain preserved. Routine dashboard interactions create no PNGs. Browser screenshots are verification evidence under outputs/reports/browser_checks/process_map, not visualization inputs.

## Automated verification

Commands executed with the project .venv Python:

- `python -B -m pytest -q`: **82 passed, zero failed**, one optional PM4Py importer-acceleration warning, 154.97 seconds.
- `python -B -m pip check`: **No broken requirements found**.
- `python -B scripts/verify_process_map_ui.py`: actual dedicated headless Edge/CDP verification; evidence and screenshots saved in outputs/reports/browser_checks/process_map.

Regression coverage includes independently expected DFG counts, readable/original labels, edge filtering and count preservation, false-edge rejection, singleton/hidden-edge isolation, selected activity statistics, complete activity inventory, layout spacing/aspect and Streamlit controls including all edges and empty threshold. Existing Day 1-5 tests and historical data fingerprints pass. A date-widget warning cleanup caused three failures during development and was fully reverted before the final passing run.

## Browser and performance checks

Actual Edge opened the running application. Inspected live chart options match seven default links and all 39 links/17 nodes, with original frequencies. Real wheel and pointer-drag input changed zoom and graph position. Full-graph rendered node bounding boxes showed no overlaps in the checked desktop state. Selecting Saved showed 135 occurrences and the 134-singleton explanation, with its isolated node visible in the main-path view. No rendered app exceptions; a simulated 390px mobile viewport had 390px document width. Desktop main/full and mobile screenshots were opened and inspected. Final run details are in verification.json.

Three local Python preparation-plus-inspection samples: median 0.521 s for main seven, 0.395 s for all 39 (outputs/reports/process_map_ui_performance.json). A browser run reached the first graph in about four seconds. These are local observations, not production guarantees or a comparable speedup over the earlier Plotly spec-only timing. Dependencies are unchanged.

## Files and limits

New reusable process_map_data.py, regression tests/test_process_map_ui.py and scripts/verify_process_map_ui.py; updated process_mining_charts.py, ui_mining.py, day2.py, scripts/run_day2.py, mining/Day 2 tests and documentation. Application text encoding was normalized while preserving existing filter behavior.

Dense full graphs still have arrow crossings; optional edge labels can overlap, so hover is the default. Pan/zoom and focus are necessary on small screens. Browser coverage is desktop Edge with simulated mobile sizing, not every device/browser. Activity selection uses the linked selector, not node clicks. No deployment or Day 6 work performed.

Final text/tooltip-only follow-up: python -B -m pytest -q tests/test_process_map_ui.py: 9 passed in 39.45 seconds. Final browser first-graph readiness: 4.364 seconds; all checks passed.
