# Day 2 methodology and observed findings

Scope: data quality, reproducible preprocessing and initial descriptive exploration of the actual DomesticDeclarations.xes file. No ML, recommendations, simulation, LLMs, agents or dashboard implemented.

## Observed quality

10,500 traces/cases; 56,437 events; 17 activities; ten original flattened columns. No nulls, invalid required fields, invalid observed attribute types, exact duplicate records, duplicate event IDs, duplicate trace names, empty traces, case-attribute conflicts or backward timestamp steps were found by the implemented checks.

Twenty events across ten cases share a timestamp with another event in their case. Their true order is unknown; source XES order is used as the deterministic tie-breaker. Original offsets are +01:00 (23,676 events) and +02:00 (32,761 events); all are aware and parseable. Offset variation is not a defect and could reflect daylight saving; a named timezone is not established by offsets alone.

Trace length ranges from 1 to 24 events (mean 5.375, median 5). There are 134 single-event traces. With Q1=5 and Q3=6, descriptive IQR fences are 3.5 and 7.5: 365 cases fall below and 918 above them. These flags do not justify excluding cases. All 134 single-event cases end at Declaration SAVED by EMPLOYEE; zero observed elapsed duration for a one-event trace does not mean the underlying process took no time.

1,019 cases (9.70%) repeat at least one activity, totaling 1,759 occurrences beyond the first occurrence of each activity in a case. No immediately adjacent equal activities were observed. Repeated submission occurs in all 1,019 cases; repetition is a process pattern, not an exact duplicate event.

Resource labels are STAFF MEMBER (36,353 events) and SYSTEM (20,084). These are not individual worker identities. UNDEFINED role labels and activity text containing MISSING are preserved as observed categorical labels rather than automatically converted to null.

## Transformations and reproducibility

1. Audit raw XML date offsets and attribute XML types, then load through the existing PM4Py loader without its early field-validation exception so diagnostics can be saved.
2. Validate explicit mappings and this dataset's observed schema. Required fields must be present; identifiers and activities must be nonblank strings. Timestamps must be valid and timezone-aware. Amount must be finite numeric when present. Case attributes must be constant within a case, counting null versus non-null as a conflict.
3. Preserve every original attribute and record. Normalize timestamps to UTC and add `_source_order` (original zero-based flattened XES row).
4. Sort lexicographically by case identifier, UTC timestamp and source order. Original within-case timestamps were already nondecreasing. The global order changes because case identifiers are sorted as strings; source order can be recovered from `_source_order`.
5. Write Parquet, read it back and assert full DataFrame equality. Verify original XES SHA-256 remains b681556df88103c13beceb448b66501d26e92d65cc90c185c21affa2aa607b9f. Source and Parquet fingerprints are recorded.

No record-level cleaning was needed: no deletion, deduplication, imputation, activity renaming or amount conversion. Equal timestamps are retained. Original raw data stays unchanged. Re-running with the same input/environment produces deterministic tables, reports, Parquet and charts, checked with a synthetic end-to-end fixture.

## Initial descriptive statistics

| Measure | Observed value |
| --- | ---: |
| Variants | 99 |
| Mean observed elapsed days | 11.526 |
| Median observed elapsed days | 7.330 |
| 90th percentile days | 20.121 |
| 95th percentile days | 29.205 |
| 99th percentile days | 76.295 |
| Maximum observed days | 469.236 |
| Leading variant cases | 4,618 (43.98%) |

Leading variant: Declaration SUBMITTED by EMPLOYEE -> Declaration APPROVED by ADMINISTRATION -> Declaration FINAL_APPROVED by SUPERVISOR -> Request Payment -> Payment Handled. The second most frequent variant adds budget-owner approval and covers 2,473 cases (23.55%). The third skips administration approval and covers 1,392 cases (13.26%). These descriptions refer to observed sequences, not recommendations.

Starts: SUBMITTED by EMPLOYEE in 10,365 cases and SAVED by EMPLOYEE in 135 cases.
Ends: Payment Handled 10,043; REJECTED by EMPLOYEE 284; SAVED by EMPLOYEE 134; REJECTED by MISSING 30; REJECTED by ADMINISTRATION 5; REJECTED by SUPERVISOR 4. There are 457 non-payment endpoints. They can represent legitimate rejection, unfinished observation or other behavior; no definitive completion labels are assigned.

Elapsed duration is the last minus first observed event timestamp. It includes waiting and other unobserved intervals and is not active processing time. Logs can be left/right censored. No start-event semantics, SLA or resource capacity is available from these measurements.

## Output guide

JSON: data_quality_report.json (checks and source audit), preprocessing_report.json (transformations, preservation and fingerprints), initial_eda_summary.json (statistics and artifact names).

CSV: case_summary.csv (one row per case, including start/end times and descriptive flags); activity_frequency.csv; resource_frequency.csv; process_variants.csv (all 99 variants with IDs, exact JSON sequences, counts and shares); repeated_activities_by_case.csv; repeated_activity_summary.csv; starting_activities.csv; ending_activities.csv; duration_distribution.csv.

PNG: activity_frequency.png; resource_frequency.png; starting_activities.png; ending_activities.png; case_duration_distribution.png; events_per_case.png; top_process_variants.png. The full duration histogram retains the long tail; consult the quantile table for the concentration of typical case durations. PNG charts are standalone exportable artifacts.

Analytical data: data/processed/domestic_declarations_cleaned.parquet (all events and original attributes plus source-order provenance).

## Limitations

Checks identify structural violations and descriptive anomalies; they cannot establish that every real-world fact was recorded correctly. Resource categories do not support per-worker capacity estimates. Timestamp ties limit exact variant ordering for ten cases. Endpoint flags do not prove completeness. IQR length flags are statistical review aids. Results are descriptive, with no causal claims.

The C: drive filled during the first report write. Removing only pip's disposable download cache freed approximately 91 MB; project files and installed packages were preserved. Disk headroom remains limited and should be increased before later development. A one-case synthetic test exposed undefined standard deviation serialization; undefined statistics now become JSON null instead of invalid NaN.
