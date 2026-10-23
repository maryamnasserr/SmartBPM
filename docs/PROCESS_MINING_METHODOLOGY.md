# Process mining methodology and metric definitions

Data source: the validated local `data/processed/domestic_declarations_cleaned.parquet`, preserving all original XES records and `_source_order` provenance. Routine dashboard interactions do not read XES or saved PNGs. The global activity/resource/date/duration filters select complete cases using the existing Day 3 contract.

## Ordering and discovery

Canonical event order is case identifier, UTC timestamp, then original zero-based source row. Events with tied timestamps retain source order; this is deterministic, not evidence of causal precedence. Discovery operates on consecutive events within a case, never across case boundaries.

Frequency discovery uses PM4Py's Pandas directly-follows backend (`get_dfg_graph`, frequency mode, window=1), with both backend sorting options disabled after canonical sorting. `start_timestamp_key` is explicitly the observed event timestamp, preventing the backend from creating a synthetic start-time attribute. Independent vectorized adjacency counts must exactly equal PM4Py's results. Total edge occurrences must equal events minus nonempty cases.

This is a directly-follows graph (DFG), not a BPMN or Petri-net model. It summarizes observed adjacency and does not infer gateways, concurrency, causal effects or every permitted process execution. An additional formal discovery model was deferred to prioritize clear, stable rendering of observed behavior over unsupported control-flow interpretation.

PM4Py references: [DFG API and frequency semantics](https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html), [DFG examples](https://processintelligence.solutions/pm4py/examples/directly-follows-graph). The installed PM4Py 2.7.23.11 backend source/signature was checked for ordering and timestamp behavior.

## Metric dictionary

| Metric | Definition/calculation | Assumptions and interpretation | Limitations |
| --- | --- | --- | --- |
| Case/event/activity counts | Unique case IDs, event rows, unique observed activity labels in selected complete cases | No records removed within selected cases | Reflect the log, not all real-world behavior |
| Case elapsed days | (Last observed timestamp minus first) / 86,400 seconds | UTC; one duration per case | Includes waiting/unobserved intervals; not active processing time; observation boundaries can censor cases |
| Case duration percentiles | Pandas linear-interpolated quantiles across case elapsed days | Empirical descriptive distribution | Small groups give unstable percentile estimates; no SLA implied |
| Transition occurrence frequency | Count each consecutive source-target pair in each ordered case, including repetitions | PM4Py counts verified independently | Not unique cases, causal influence or enabled future behavior |
| Transition case count | Distinct case IDs containing the consecutive pair | A case contributes once to this column | May be lower than occurrence frequency |
| Transition elapsed gap hours | (Next event timestamp minus current event timestamp) / 3,600 seconds for each consecutive pair | Nonnegative canonical timestamps; zero ties retained | Not independently measured service time or resource queue waiting time |
| Transition mean/median/p90/p95/max | Aggregate gap hours over occurrences of that edge | Repeated occurrences contribute separately | Extreme/sparse observations and uncertain tied-event order affect interpretation |
| Zero-gap occurrences | Number of consecutive pairs sharing an observed timestamp | Zero timestamp difference retained | Does not establish instantaneous work or parallelism |
| Process variant | Exact ordered activity-label tuple for a case | Preserves repeated activities; tied-event order follows provenance | No inferred gateways/concurrency; ranks can change under filters |
| Variant case share | Cases with sequence / all cases in selected cohort | Sum of all variant shares is one | Top-ten chart does not represent all cases unless their shares sum to one |
| Variant duration statistics | Mean/median/min/max/p90/p95 elapsed days of cases assigned to sequence | One duration per case | Small sample size, route selection and censoring limit comparison |
| Repeated activity type | Activity occurs at least twice in one case | Counts exact labels, not semantically equivalent tasks | Not automatically duplicate records, defects or unnecessary work |
| Excess occurrences | Sum(max(activity count per case minus one, zero)) | All occurrences retained | Does not quantify avoidable work or its duration |
| Repetition group duration | Case elapsed statistics for cases with/without any repeated activity | Groups partition the cohort for this comparison | Associations can reflect case complexity and other confounding; not causal effects |
| Repeated approval/rejection subsets | Cases repeating a label containing APPROVED or REJECTED tokens (including FINAL_APPROVED) | Lexical categories based on actual dataset labels | Subsets overlap; not additive totals, inferred outcomes or proof of waste |

## Interactive map display

Native Streamlit ECharts SVG draws readable activity/role boxes and directed arrows with occurrence-scaled widths, optional count labels and exact-name tooltips. Deterministic directed ranking prioritizes frequent forward paths only for layout; all selected relationships, including loops, remain present. Main-path default shows seven frequent edges; all-transition mode reveals the complete cohort graph. Activities without visible relationships remain explicitly listed and inspectable, with reasons. Zoom/pan and the separate activity selector provide exploration. Generated Axx identifiers are presentation codes, not original dataset codes. See PROCESS_MAP_UI_VERIFICATION.md for browser evidence and layout limitations.

Frequency minimum, maximum edge count and optional activity focus select existing edges for display only. They do not delete intermediate events, bridge paths, recompute variants, change the case cohort or establish that hidden edges do not exist. Coverage states displayed relationships/occurrences against full cohort totals. A focus includes real edges touching a selected activity; empty focus means all edges, unlike an empty global activity selection, which means no cases.

All cohort transition statistics remain inspectable/exportable even when some edges are hidden. Map count labels can be disabled to reduce clutter. Exact sequences, counts, group statistics and elapsed distributions are available in tables/CSV. Controls apply no undocumented SLA or process-time assumption.

## Exports and preservation

CSV exports contain exactly the table named by their control, without a DataFrame index: selected cases, displayed transitions, all cohort transitions, variant performance, repetition group statistics or case repetition flags. Displayed-edge exports intentionally differ from full-transition exports when complexity controls hide edges. Export buttons use `on_click="ignore"` to avoid an unnecessary rerun.

The raw and processed dataset fingerprints remain checked against Day 2. New small reports are prefixed `day4_5_` or `day5_`; earlier validated reports are preserved. Test/browser download copies are checked and removed after verification, not retained as duplicate datasets.


## Day 6 workspace update

Main Process and Detailed Process replace the earlier main-path/all-transition labels. Default layout is left-to-right with observed start/end activity colors, a separate selection highlight and mobile vertical rearrangement. These colors represent recorded case boundaries; an activity can be both a boundary and an intermediate step. Display codes remain generated identifiers. The complete underlying DFG and frequency semantics above are unchanged. Activity details include exact incoming/outgoing relationship counts and median observed gaps, not active processing durations. See DAY6_UI_VERIFICATION.md for final browser checks and DAY6_ML_PROBLEM_DEFINITION.md for the proposed performance target.
