# SmartBPM user testing guide

This guide covers the historical and preparation pages from Days 1–8. Days 9–10 add trained models and a historical-validation Predictive Analytics page; see [DAY9_10_ML_RESULTS.md](DAY9_10_ML_RESULTS.md) for its walkthrough. SmartBPM does **not** claim live organizational predictions.

## Start the application

Open PowerShell in the project directory and run:

```powershell
Set-Location 'C:\Users\Maryam Nasser\Desktop\SmartBPM'
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8504 --browser.gatherUsageStats false
```

Open **http://localhost:8504**. Leave the terminal running; press Ctrl+C there to stop the application. If that port is occupied, use `--server.port 8505` and open the matching address. You do not need to recreate the environment or reinstall packages for ordinary use.

The cleaned dataset and generated preparation reports must be present. If ML Preparation says its artifacts are missing, run `.\.venv\Scripts\python.exe scripts/prepare_ml_dataset.py` from the project directory, then revisit the page. This regenerates preparation artifacts without training a classifier. The application displays an explicit error if the cleaned analytical dataset is missing; do not substitute an unrelated dataset to obtain the expected figures.

## Learn the shared controls

- **Explore:** use the sidebar radio buttons to change pages. On a narrow screen, open the sidebar with the top-left chevrons. Scroll the page for tables below charts.
- **Case:** one declaration identifier. **Event:** one recorded activity in that declaration. A case can have repeated events of the same activity.
- **Selected cases/events/activities:** these four top cards describe the selected group. With Reset filters, expect 10,500 cases, 56,437 events, 17 activity types and median 7.33 observed days.
- **Activity selection:** expand it, then keep activities you want a case to contain. Multiple selected activities mean **any**, not all. Clear all to deliberately test an empty group. Type to search a long list.
- **Resource:** broad recorded categories, STAFF MEMBER and SYSTEM; not named people or employee capacity. Multiple resources mean any. Activity and resource may match different events of the same case.
- **Case start date (UTC):** selects cases by their first recorded date, with both dates included. It does not cut later events off selected cases. The default case-start window ends 29 December 2018, while some later case events extend to June 2019; this is expected.
- **Applying dates:** use the calendar button and choose both ends of the range; choosing the same day twice gives a one-day window. Confirm the **ACTIVE FILTERS** caption has changed before reading results. Editing a displayed date segment alone may leave an uncommitted date until the range is completed.
- **Observed case elapsed days:** last minus first recorded timestamp, including waiting. It is not active work time. The slider's full upper bound is rounded up to 470 days; the actual maximum is about 469.236 days.
- **Reset filters:** restores all activities, both resources, the full start-date window and the full duration range. It resets the cohort filters; it does not promise to reset every process-map display control or selected tab.
- **Combining controls:** conditions across activity, resource, date and duration must all match. Empty selection produces zero cases and an explanatory message, not an application error.
- **ML research exception:** ML Preparation and the research definition inside Performance Investigation use the frozen full-dataset design. Sidebar filters change historical charts, not the research threshold or chronological partitions.
- **Charts:** hover for exact values. Plotly charts support drag zoom and double-click reset. The process graph uses scroll zoom and drag pan instead. Tables have their own scrolling area; mobile tables may require horizontal scrolling within the table.
- **Refresh:** the application reconnects and can return to its default Overview/full-cohort state. Browser refresh is not a saved-workspace feature. Use the sidebar to return to your page.

## Test every page

### Overview

Read the top cards, then inspect **Case elapsed duration** and **Events per case**. The first counts cases by recorded elapsed days; the second counts cases by number of events. The duration table includes mean 11.52572198, median 7.33028935 and p95 29.20535359 days for the full dataset. A long tail is expected; do not treat a large value as a data error automatically.

Hover a bar, drag a zoom box and double-click to restore the chart. Change a filter and confirm the top cards and charts change together. Click Reset filters and confirm the original cards return.

### Activities & resources

The bars count **event occurrences**, not distinct cases. The full-data submission activity occurs 11,531 times even though there are only 10,500 cases, because a case may submit again. Resource counts are STAFF MEMBER **36,353** and SYSTEM **20,084**, adding to 56,437 events.

Hover a bar and expand **Inspect activity counts** or **Inspect resource counts** for the exact table. A displayed label may wrap onto a second line; the original activity text remains available. Apply the walkthrough filter below and expect the case's full 18-event history to contribute, rather than just its one matching event.

### Variants & repetition

A **variant** is an exact ordered activity sequence. The full dataset has **99** variants; the two largest contain **4,618** and **2,473** cases. The chart shows the ten most common; the table contains all variants. Generated IDs such as V0001 describe the ranking in the current cohort and can change when filters change.

**1,019 cases** repeat at least one activity. A repeat can be legitimate additional review or resubmission; it is not automatically waste or an error. Hover a variant bar for the sequence/share, inspect the full table, and compare it after filtering. For duration comparisons and a variant selector, use Process Mining → Variant performance.

### Case boundaries

This additional page shows each case's first and last recorded activities. Each chart totals 10,500 cases with full filters. An ending activity does not establish that the case truly completed. A non-payment endpoint can reflect rejection, an alternative ending or incomplete observation.

Change a filter and check both charts still describe the same selected cases. They count case starts/ends rather than all activity occurrences.

### Case explorer

The first table summarizes every selected case. **Inspect a case** selects the event-history table underneath it; it does not narrow the entire cohort. Search the selector by typing a case ID. Event histories use UTC timestamps and deterministic source order for ties; tied timestamps do not prove causal order.

Click **Download selected case summary**. The CSV contains one row per selected case, not the selected case's raw events. Open it in Excel or another CSV reader and check the case identifier, event count and elapsed days. If you want one row in this export, first narrow the cohort to one case using the walkthrough activity filter.

### Process Mining

The full-data cards show **45,937 observed transitions**, **39 distinct relationships** and **99 variants**. A transition is a consecutive pair of recorded events within a case. One relationship can occur many times; `events − cases = 56,437 − 10,500 = 45,937` because every nonempty case contributes one fewer pair than events.

In **Process map & transitions**:

1. Start with **Main Process**: the default view shows at most seven frequent relationships. It is not a single case route, and hidden edges remain in the data.
2. Scroll over the graph to zoom and drag to pan. Hover an arrow for its occurrence count.
3. Change **Minimum transition frequency**, **Maximum displayed edges** or **Focus on activities**. These affect graph visibility, not the cohort KPIs.
4. Choose **Detailed Process** to show all 39 relationships. The frequency/edge-limit/focus controls are disabled because this mode bypasses them.
5. Try **Reading direction** and **Show edge frequency labels**. Use fewer edges or hide counts if the graph becomes crowded. Detailed graphs can need pan/zoom on small screens.
6. Select **Declaration SAVED by EMPLOYEE** in **Inspect an activity**. Full-data details should show 135 occurrences; its isolation explanation includes 134 single-event cases. An activity outside the visible main flow has not been deleted.
7. Inspect transition tables and use **Export displayed transitions** versus **Export all cohort transitions**. In Detailed mode both exports contain 39 relationships; in Main mode their row counts can differ.

In **Variant performance**, select a variant, read its complete sequence and case count, and add/remove variants in the comparison control. Clearing comparisons should show a request to choose at least one, rather than an error. Box plots compare recorded case durations. Export the variant performance table if desired.

In **Repetition & duration**, compare group durations and export statistics or case flags. Approval/rejection repetition subsets can overlap; they are not additive totals. Differences are associations and do not prove repetition caused delay.

### Performance Investigation

Full filters show mean observed duration **11.53 days**, repeating-activity share **9.7%** and **99 variants**. Inspect all four tabs:

- **Longer cases:** duration histogram, percentiles and descriptive candidate thresholds. The dashed research line is frozen from training data, not recomputed when you change the cohort.
- **Repeated activities:** duration comparisons and repeated labels; these do not establish avoidable work.
- **Alternative paths:** variant frequency versus median duration. There are 77 variants with fewer than ten cases each, covering 166 cases. Small groups are uncertain, not necessarily faulty.
- **ML research design:** selected historical target, Event-2 reachability and historical distributions. **10,366 Event-2 snapshots** is not the final 9,536-row unresolved ML dataset. It includes cases already over threshold and cases later excluded for overlap. Day 6 candidate features are distinguished from the implemented primary set.

Check that the research threshold remains **11.105428240740741 days** after changing a cohort filter. No accuracy, recall or live predictions should appear. Candidate/investigated-variant CSV downloads are historical research summaries.

### ML Preparation

This page explicitly distinguishes historical labels/preparation statistics from predictions and directs you to Predictive Analytics for saved-model validation results. The test set remains locked.

The top cards show **9,536** unresolved cases, the displayed rounded threshold **11.105428240741**, and **333** already-over-threshold cases. The full-precision value is in the reports. Exclusion accounting is:

| Group | Cases | Meaning |
|---|---:|---|
| Fewer than two events | 134 | No Event-2 snapshot |
| Already over threshold | 333 | Positive label already known at prediction time |
| Additional overlap exclusions | 497 | Historical outcome crosses the next evaluation cutoff |
| Unresolved eligible | 9,536 | Final ML dataset |
| Original total | 10,500 | Groups reconcile without duplication |

The original overlap count is 520; 23 are also known positives and are counted in that group above. The threshold is the training-only p75 of 5,951 mature Event-2 training cases, frozen before removing known positives. It is a research cutoff, not an official SLA.

| Partition | Cases | Historical positive | Historical negative |
|---|---:|---:|---:|
| Train | 5,783 | 1,320 | 4,463 |
| Validation | 1,752 | 496 | 1,256 |
| Test | 2,001 | 668 | 1,333 |

Validation starts 27 June 2018 at 09:27:50 UTC; test starts 12 October 2018 at 13:06:56 UTC. Equal prediction timestamps stay together. Training/validation outcomes reaching the next cutoff are purged. This is a retrospective approximation: a recorded endpoint cannot certify true completion.

The six predictors are first activity, second activity, elapsed hours between them, UTC month, weekday and hour. Future events and final attributes do not enter them. Case IDs, timestamps, split and target are metadata, not predictors. Resources and roles remain sensitivity-only until their availability at Event 2 can be confirmed. Preprocessing statistics/vocabularies use unresolved training rows only.

Clear activity/resource filters elsewhere, then visit this page: it should still show 9,536 because these are frozen full-dataset preparation results.

## Complete walkthrough: declaration 108210

This real case demonstrates complete-case filters, repeat handling, historical duration and the early ML snapshot.

1. Open **Overview** and click **Reset filters**. Confirm 10,500 cases, 56,437 events, 17 activities and median 7.33 days.
2. Expand **Activity selection**, clear its selection, type and choose **Declaration FOR_APPROVAL by ADMINISTRATION**. Leave both resources, all dates and all durations selected.
3. Expect **1 selected case, 18 events, 11 activity types and 33.81 days**. The selected activity occurs once in the entire log, identifying this case. All its other events remain included.
4. Open **Case explorer**. Select **declaration 108210** if necessary. Its first event is submission on **10 April 2018, 20:00:59 UTC**; its last is Payment Handled on **14 May 2018, 15:31:21 UTC**. Their difference is **33.81275462962963 days**. The second event is administration rejection on **10 April 2018, 20:21:08 UTC**.
5. Download the selected case summary. It should contain exactly one data row with case ID `declaration 108210`, event_count 18 and elapsed_days about 33.81275463.
6. Open **Activities & resources**. Submission occurs **5** times, administration approval **3** times and employee rejection **2** times in this case. There are **16 STAFF MEMBER events and 2 SYSTEM events**.
7. Open **Variants & repetition**. Expect one variant and one case with repeated activities. There are three repeated activity types, with seven excess occurrences in total. Repeat labels do not establish the cause of delay.
8. Open **Process Mining → Detailed Process**. Expect **17 transition occurrences**, **14 distinct relationships** and **1 variant**. Transition occurrences equal 18 events minus one. Repeated directed pairs explain why 14 relationships represent 17 occurrences.
9. Open **Performance Investigation**. Its historical mean/median for this one-case cohort are about 33.81 days; the research design remains anchored to the full dataset.
10. Open **ML Preparation**. It returns the frozen preparation figures, including 9,536 eligible rows. The exported ML row for this case is in **train**, with historical target **1**: 33.81275 days exceeds 11.10542824 days. At Event 2, only **20 minutes 9 seconds** had elapsed (**0.3358333333 hours**), so it was not already known positive. Its later rejections, approvals and payment must not enter the predictors. This label is derived from history; it is not a model prediction.
11. Return to Overview and click **Reset filters**. Confirm all original cards return. Test clearing resources to see the empty-state message, then reset again.

## Run verification yourself

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/audit_uat_data.py
```

The independent audit recomputes results directly from the raw XML and cleaned rows rather than importing SmartBPM analytical helpers. It also compares the ML export and train-only preprocessing statistics. It writes `outputs/reports/uat_data_audit.json` without changing the source data.

For a manual checklist, repeat the page actions above, then test a narrow browser window, refresh, empty activity/resource selections, reset, a date range and a duration range. If anything fails, record the page, selected filters, exact actions, expected result, actual result and any error text. A screenshot is useful. See [SMARTBPM_UAT_REPORT.md](SMARTBPM_UAT_REPORT.md) for the verified scope and remaining limitations.
