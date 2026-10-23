# SmartBPM application acceptance report

Verification date: 20 October 2026 (Africa/Cairo). Scope: existing Days 1–8, before Day 9. The application was launched locally with Python 3.12 and the existing virtual environment. No dependencies were added, classifier trained, research threshold changed, or recommendation/simulation functionality implemented.

## Independent data verification

`scripts/audit_uat_data.py` reads the raw XES with Python's XML parser and independently computes sequences, directed pairs and elapsed durations with Pandas and Counter. It does not import SmartBPM analytical modules. The raw case/activity/timestamp rows match the cleaned Parquet in source order. Original and cleaned file hashes still match the Day 2 provenance report.

| Measurement | Independently verified result |
|---|---:|
| Cases | 10,500 |
| Events | 56,437 |
| Activity types | 17 |
| Exact variants | 99 |
| Distinct directed relationships | 39 |
| Consecutive-pair occurrences | 45,937 |
| Cases repeating an activity | 1,019 |
| Mean observed days | 11.525721979717813 |
| Median observed days | 7.330289351851851 |
| p95 observed days | 29.20535358796295 |
| Maximum observed days | 469.23631944444446 |
| ML-ready unresolved cases | 9,536 |
| Frozen research threshold, days | 11.105428240740741 |

Every ML row was independently compared with the original case's first two events, timestamps, elapsed prefix, calendar values, historical target and chronological partition. The export has unique case IDs and exactly the approved features plus metadata. Training-only imputation/scaling statistics and category vocabularies were independently recalculated and matched. All 39 saved transition frequencies matched independent pair counts.

| Final partition | Cases | Positive | Negative |
|---|---:|---:|---:|
| Train | 5,783 | 1,320 | 4,463 |
| Validation | 1,752 | 496 | 1,256 |
| Test | 2,001 | 668 | 1,333 |

Accounting: 10,500 = 134 singletons + 333 already-over-threshold cases + 497 additional overlap exclusions + 9,536 unresolved snapshots. There are 520 original overlap cases, of which 23 are already-over-threshold; the mutually exclusive accounting avoids duplication. The threshold is the linear-interpolated p75 of 5,951 mature Event-2 training outcomes before threshold-dependent known-positive removal, not a full-log threshold. Validation starts 2018-06-27T09:27:50 UTC and test starts 2018-10-12T13:06:56 UTC. Equal prediction timestamps remain together; crossing outcomes are purged.

The target remains total observed duration strictly exceeding the threshold. It is not remaining duration or an organizational SLA. Six predictors use only the recorded prefix: first/second activities, prefix elapsed hours and UTC month/weekday/hour. IDs, absolute timestamps, target and split are metadata; future outcomes/history and final case attributes are excluded. Resources/roles remain sensitivity-only. Existing mutation tests check future-feature independence and training-only threshold/preprocessor fitting. Test outcomes are inspected for required preparation audits, not model tuning or performance claims.

Evidence: `outputs/reports/uat_data_audit.json`. Independent audit execution measured 12.447 seconds on this machine; no production performance guarantee is implied.

## Verified issues and corrections

| Issue | Reproduction/evidence | Correction |
|---|---|---|
| Duplicate widget-default/session-state warning | Run app, clear activities, click Reset filters. Streamlit logged that key `activities` had both a default and a Session State value. No calculation exception occurred. | Initialize filter values once in session state; omit competing widget defaults. Range/date initialization and reset behavior are regression-tested. Warnings were not suppressed. |
| Ambiguous Event-2 “eligible” wording | Performance Investigation called 10,366 cases eligible while ML Preparation showed 9,536 unresolved cases. Both calculations were correct but the different cohorts were easy to confuse. | Label 10,366 as Event-2 snapshots, explain known-positive/overlap inclusion and direct users to the final ML Preparation cohort. Distinguish Day 6 candidate resource/role features from primary features. |
| Unclear filter time semantics | Case-start date window ends in 2018 while retained cases can have events in 2019. This is correct complete-case filtering. | Add date/duration help text explaining case-start selection, complete histories and elapsed versus active time. |

Source dataset and research methodology were preserved. Changed application files: `app.py`, `src/smartbpm/ui_performance.py`. Regression coverage: `tests/test_uat.py`; existing performance assertions and `scripts/verify_day6_browser.py` were updated for the clearer label.

## Automated checks

- Baseline before application edits: **114 passed**, one optional PM4Py accelerator warning, **173.78 s**.
- Final full `python -m pytest -q`: **116 passed**, one existing optional PM4Py warning, **164.16 s**.
- Final `python -m pip check`: **No broken requirements found**.
- New reset regression checks all four filter values, empty-state navigation to ML Preparation, full-cohort restoration and absence of the duplicate-default warning. New research-view check verifies the distinction between landmark and final eligibility.
- An intermediate run had one stale assertion for the replaced “Eligible cases” label; it was updated to the intended “Event-2 snapshots” wording. An initial new test read captions as Markdown; its selector was corrected. Both were test-maintenance failures, and the final complete run passes.

AppTest emits a known bare-mode `missing ScriptRunContext` logging warning when instantiated outside a Streamlit session; this is distinct from rendered application exceptions. The optional `r4pm` accelerator warning remains because that dependency is not installed. Neither warning was hidden by configuration.

## Page and interaction coverage

The actual application was opened in headless Microsoft Edge through its browser debugging interface, rather than relying solely on Streamlit AppTest. Desktop viewport: 1440×1100. Simulated mobile viewport: 390×844. Page screenshots and machine-readable results are under `outputs/reports/browser_checks/uat/`.

| Page | Checks |
|---|---|
| Overview | KPI totals and median; histogram case count; chart zoom/reset; activity/resource/date/duration controls and reset; empty group; browser refresh |
| Activities & resources | Both plotted frequency dictionaries matched independently counted raw records; cohort consistency; count tables and responsive layout |
| Variants & repetition | 99 variants, 1,019 repeating cases, cohort consistency and mobile layout |
| Case boundaries | Both endpoint charts, cohort consistency and mobile layout; endpoints explained as recorded observations |
| Case explorer | Case selection; complete histories checked against independent records; full/filtered summary export actions and CSV integrity |
| Process Mining | Main seven-edge and Detailed 39-edge views; exact frequencies totaling 45,937; wheel zoom, drag pan, activity selection, reading direction, variant selection, comparison/repetition tabs and exports |
| Performance Investigation | Mean duration and repeat prevalence; all four tabs; unchanged threshold; historical/research distinction; candidate and investigated-variant exports |
| ML Preparation | 9,536 unresolved rows, displayed rounded threshold, 333 known positives, preparation tables and explicit no-trained-model explanation; frozen figures remain accessible with empty cohort filters |

**Final main browser run passed.** All eight page checks recorded zero rendered exceptions and document/viewport widths of 390px in simulated mobile. No browser-console errors were captured. The run verified the actual calendar selection (11 January 2017: independently confirmed 2 cases / 12 events), duration slider, activity/resource empty groups, resets, refresh, fixed research statistics under empty filters, graph controls and export actions. All eight retained CSVs passed content checks: 39-row full/displayed transition tables totaling 45,937 occurrences; 99-row variant/investigated tables; 10,500 case flags; four repetition groups; three candidate targets; and the one-row walkthrough case summary. Nine download-button actions included both full and filtered summary exports; the last retained main-run summary is the filtered version.

**Final supplemental browser run passed.** Checked frequency filtering to an empty graph while retaining underlying KPIs, maximum edge count, activity focus, Detailed-mode bypass, edge-frequency labels, empty/reselected variant comparisons and actual mobile sidebar navigation. A separate full-cohort CSV download was read back: 10,500 unique case rows and event_count sum 56,437. Supplemental rendered exceptions: zero. Detailed graphs with frequency labels remain crowded; inspected desktop/mobile graph screenshots demonstrate why zoom/pan or hidden labels can be needed.

Final evidence: `outputs/reports/browser_checks/uat/verification.json`, `controls_verification.json`, desktop/mobile page PNGs, `graph_frequency_labels.png`, `graph_mobile.png`, eight main CSV exports under `downloads/`, and the full-cohort summary under `control_downloads/`. Screenshots were directly inspected for the principal page/graph layouts and mobile presentation. Final results are authoritative; intermediate failure captures are retained separately under `intermediate_attempts/`.

Consolidated status: `outputs/reports/uat_verification_summary.json`. Final source hashes were rechecked after QA, server health returned `ok`, the temporary browser profile was removed, and retained browser evidence occupies 6,500,698 bytes (about 6.2 MiB).

Browser automation required selector/readiness fixes for progressively rendered widgets, input values versus body text, the download-hub tab, disposed chart instances and the transient empty document during refresh. Reset-to-navigation sequences needed to wait for reset completion rather than dispatch two widget events immediately. Calendar testing was changed to complete a range rather than assume an uncommitted segment edit applied the filter. Supplemental controls required the actual checkbox input and current sidebar-toggle selector, fresh initial UI state and a corrected helper import. A debugging screenshot timeout required restarting the dedicated browser. These intermediate harness failures were resolved and are not counted as successful checks. No additional application calculation defect was found.

## Verified real-case walkthrough

`declaration 108210` contains the log's single `Declaration FOR_APPROVAL by ADMINISTRATION` event. Selecting that activity retains **one full case, 18 events, 11 activities and 33.81 days** in the dashboard. Independent history: submission 2018-04-10T20:00:59 UTC to Payment Handled 2018-05-14T15:31:21 UTC, **33.81275462962963 days**. There are 17 transition occurrences and 14 distinct relationships. Submission repeats five times, administration approval three and employee rejection twice.

Its Event-2 snapshot occurs at administration rejection on 2018-04-10T20:21:08 UTC, only 20 minutes 9 seconds after submission. Its training historical label is 1, while its already-over-threshold status at prediction time is false. Later approvals/rejections/payment are not predictors. The complete manual walkthrough is in [SMARTBPM_USER_TESTING_GUIDE.md](SMARTBPM_USER_TESTING_GUIDE.md).

## Remaining limitations and readiness

Observed endpoints do not certify completion or prompt outcome ingestion; censoring remains unknown. Tied timestamps preserve source order, not proven causality. Singleton exclusion and endpoint purging introduce selection bias; the historical holdouts have already been inspected for research design. Resource/role arrival-time availability is unverified. These limits predate QA and remain documented; no numerical correction was necessary.

Dense Detailed graphs need zoom/pan or fewer visible labels, especially on narrow screens. Wide tables scroll internally; simulated mobile is not a physical-device or cross-browser guarantee. A refresh can start a new UI session. Browser rendering/interaction coverage cannot prove absence of all errors. This is a thesis prototype rather than a production deployment certification.

**Ready for Day 9 within the documented thesis scope:** automated tests, independent data checks and both final browser suites pass, with no unresolved blocking application defect found in this verification. This is a readiness judgment based on tested paths, not a promise of zero errors. Retain the censoring, availability and evaluation-selection limitations when designing future baselines/models.

No predictive performance is claimed. No model, recommendations, simulation or Day 9 implementation was started. Launch commands, every-page checks, expected results, export semantics and troubleshooting steps are in the user guide. The dedicated QA browser/profile was closed/removed after verification; Streamlit remains available at http://localhost:8504 for the user's walkthrough.
