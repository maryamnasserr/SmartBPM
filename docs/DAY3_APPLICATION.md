# Day 3: interactive Streamlit application

Run from `C:\Users\Maryam Nasser\Desktop\SmartBPM` with the project's Python 3.12 environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the URL printed by Streamlit, normally http://localhost:8501. If PowerShell blocks environment activation, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app reads `data/processed/domestic_declarations_cleaned.parquet`. If absent, run `python scripts/run_day2.py` with the same environment. The app never regenerates outputs automatically. It can also be launched with an absolute app.py path from another directory; data paths are anchored to the project.

## Interface

Five views: Overview; Activities & resources; Variants & repetition; Case boundaries; Case explorer. Full-dataset cases/events/activities and UTC event range remain visible above clearly labeled selected-cohort metrics.

Eight Plotly figures are computed from the selected underlying records: activity frequency, resource frequency, observed case elapsed duration, events per case, top ten variants, repeated activity patterns, starting activities and ending activities. Hover for details, drag to zoom, double-click to reset axes and use Plotly's toolbar. Zoom is a chart view operation; it does not change cohort statistics.

The Case explorer provides a sortable/searchable case summary, CSV download and event-level inspection of a selected case. The complete variant table accompanies the top-ten chart. Variant IDs are ranked within each selected cohort and can change after filtering; exact sequences define variants.

## Filter contract

Activity and resource selections find matching cases and retain every event of each selected case. Multiple choices within one filter use OR. Categories combine with AND. Activity and resource matches may occur at different events in a case. Consequently charts can include activities/resources other than the selected matches; they describe the complete histories of the selected cases. This preserves valid elapsed durations, endpoints and variants.

The date range is inclusive and applies to UTC case start date, not to individual event timestamps. Complete histories can extend beyond the chosen date window. The duration slider is inclusive and filters full observed elapsed days. Empty activity/resource selections safely produce zero metrics and a no-results message. A partially entered date range asks for both endpoints. Reset restores the full cohort.

The activity multiselect is in a collapsed expander to keep the date/duration controls easy to reach despite 17 long activity names. At narrow screen widths Streamlit stacks columns and collapses the sidebar. Open it using the top-left control to access navigation and filters.

## Architecture and caching

`app.py` owns presentation, Streamlit widgets and bounded cache wrappers. `src/smartbpm/dashboard.py` owns read-only Parquet validation, reusable complete-case filtering and data preparation. It reuses Day 2's quality_report and describe_process. `src/smartbpm/dashboard_charts.py` constructs Plotly figures from analytical tables. Saved PNGs and JSON summaries are not dashboard chart inputs.

Dataset caching includes source path, size and modification time. Analysis/cohort caches depend on the actual input frame and filter values and have bounded entry counts. No global mutable shared DataFrame or persisted app-generated dataset is used. `.streamlit/config.toml` supplies the light teal theme and disables usage telemetry.

Dependencies added: Streamlit 1.66.0 and Plotly 7.1.0 with their resolved dependencies. Streamlit requires Pillow below 13, so pip resolved Pillow 12.3.0; all regression checks cover the resulting environment. Exact complete versions are recorded in requirements.txt.

## Interpretation

Elapsed duration is the last minus first observed timestamp, including waiting and unobserved intervals, not active processing time. Counts do not establish causal bottlenecks. Repeated activities can be rework signals but are not automatically waste or defects. Non-payment endings do not prove incompleteness. Logs may be censored, timestamp ties have uncertain causal order, and STAFF MEMBER/SYSTEM are broad categories rather than individual workers.

## Verification artifacts

`tests/test_dashboard.py` checks whole-case filtering, date/duration inclusivity, empty selections, attribute preservation, Parquet validation, chart data, input immutability, original dataset fingerprints and real Streamlit execution with AppTest. AppTest navigates every view and exercises activity/resource/date/duration filters, empty selections and reset.

A separate real-browser check uses a hidden headless Edge instance and Chrome DevTools Protocol through the installed websockets dependency. It is not required to run the app. `scripts/verify_dashboard_browser.py` expects the app at 127.0.0.1:8501 and a dedicated browser debug session on port 9222. It verifies real DOM totals, eight chart views across navigation, pointer drag zoom, keyboard duration filtering, reset, mobile width and absence of rendered exceptions. It does not install or launch browsers itself.

Evidence: outputs/reports/dashboard_browser_verification.json; dashboard_desktop.png; dashboard_activities.png; dashboard_variants.png; dashboard_mobile.png. Screenshots are verification/documentation outputs, never analytical chart inputs.

## Known limitations

This is descriptive decision support, without ML, recommendations, simulation or a dashboard for live operational control. Date filters use case starts and activity/resource filters operate on whole cases; use the stated contract when interpreting charts. Very small cohorts may have undefined statistics. Browser verification uses desktop Edge and a simulated mobile viewport, not physical devices or every browser.

C: disk space remains limited. Installation first failed because of insufficient space; clearing only regenerable .venv bytecode caches allowed completion. No raw/processed data or earlier reports were removed. Increase free disk space before installing further features. Day 3 is the current stopping point; later work requires explicit approval.
