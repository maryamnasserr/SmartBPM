# Day 6: ML problem definition

Days 7–8 implementation update: the target, training-only threshold and chronological boundaries below were reproduced unchanged. The final unresolved, overlap-purged ML dataset contains 9,536 cases. The 10,366 count below describes Event-2 reachability, including 333 already-known positives; overlap exclusions must account for their 23-case intersection. See [DAY7_8_ML_PREPARATION.md](DAY7_8_ML_PREPARATION.md). Resource/role attributes are sensitivity-only in the implemented primary design because ingestion availability remains unverified.

## Investigated historical problems

The source remains the validated BPI Challenge 2020 Domestic Declarations Parquet: 10,500 cases, 56,437 events, 17 activities. Historical DFG counts remain 39 relationships and 45,937 consecutive pairs. No original records were changed. No model was fitted.

| Duration statistic | Observed days |
|---|---:|
| mean_days | 11.525721980 |
| median_days | 7.330289352 |
| p75_days | 12.241634838 |
| p90_days | 20.120839120 |
| p95_days | 29.205353588 |

Candidate thresholds (strictly greater):

| Threshold days | Cases above | Share |
|---|---:|---:|
| 7.000000000 | 6211 | 59.152% |
| 14.000000000 | 2065 | 19.667% |
| 21.000000000 | 975 | 9.286% |
| 30.000000000 | 511 | 4.867% |
| 12.241634838 | 2625 | 25.000% |
| 20.120839120 | 1050 | 10.000% |

Repeated activities occur in 1,019 cases (9.7048%). The median observed span is 13.249 days with repetition versus 7.227 without; means are 23.038 and 10.288 days. Submission repeats in all 1,019, administration approval in 210 and employee rejection in 139. These are associations, not avoidable-work or causal labels. Exact variant/repetition cross-tabulations are saved in day6_investigation.json and shown in the investigated variant table.

There are 99 variants. A descriptive rare rule (<10 cases per exact sequence) identifies 77 variants covering only 166 cases. Median rare-group span is 17.054 days versus 7.319 for other paths; means 37.730 versus 11.105. Groups are sparse and heterogeneous. The two leading variants cover 4,618 and 2,473 cases. No unusual path is automatically erroneous.

## Candidate comparison and selection

day6_candidate_targets.csv evaluates all three candidates on relevance, measurability, label reliability, early feasibility, leakage, balance, interpretability, human review, simulation and timeline. Long observed span is selected: its time basis and usable class balance provide a clearer first interpretable prediction problem. Repetition is rarer and may be necessary. Rare-final-variant labels are sample-dependent, sparse and operationally ambiguous. Selection does not establish an organizational failure, actionable cause or predictive accuracy.

## Exact target

`y = 1[((last_observed_timestamp - first_observed_timestamp) / 86400 seconds) > 11.105428240740741 days]`

Equality is negative. This is a research-defined threshold, not an organizational SLA. The threshold is the linear-interpolated training-only 75th percentile after temporal overlap purging; it is frozen before validation/test feature fitting. Full-log p75 (12.241635 days) is descriptive and is not used to define the target.

The label describes recorded span, not true completion or active processing time. Cases can be censored. There are 457 non-payment endpoints and 134 singleton traces in the complete log; neither is a definitive completion label. Day 7 must report sensitivity to singleton exclusion and endpoint groups without claiming payment endpoints prove completeness.

## Prediction point and eligibility

| Point | Eligible | Excluded | At last observed time | Median prefix hours |
|---|---:|---:|---:|---:|
| First recorded event | 10500 | 0 | 134 | 0.0 |
| Second recorded event | 10366 | 134 | 5 | 0.014166666666666666 |
| First submission | 10365 | 135 | 0 | 0.0 |

Selected: immediately after the second recorded event. Canonical order is case ID, UTC timestamp, source row; only the first two rows contribute features. Simultaneous later rows are excluded. An online equivalent requires a reliable ingestion tie order; source-order tie breaking is deterministic rather than causal evidence.

At the first event, resource and role each have one unique value, and 10,365 cases share the submission activity (135 start saved). At the second event there are nine activities, two resource categories and four roles. Median elapsed prefix is 0.0141667 hours (51 seconds); 10,366 cases remain. This offers more potential signal than the first event while remaining early for most cases. Singleton exclusion is a selection bias. Five second-event landmarks coincide with the final observed timestamp; do not exclude them using future knowledge. First submission covers 10,365 but offers little extra history.

333 eligible prefixes already exceed the threshold, so their observed-span positive label is known. They need no ML prediction. 10033 have not crossed it. Report known positives separately and evaluate predictive discrimination on the latter, keeping the frozen threshold; do not advertise rediscovering already-elapsed time as future prediction. Timing-only baseline is required.

## Target distribution

| Partition | Cases | Positive | Negative | Positive share |
|---|---:|---:|---:|---:|
| all_eligible | 10366 | 3085 | 7281 | 29.761% |
| purged_overlap | 520 | 291 | 229 | 55.962% |
| test | 2074 | 741 | 1333 | 35.728% |
| train | 5951 | 1488 | 4463 | 25.004% |
| validation | 1821 | 565 | 1256 | 31.027% |

Unknown-at-prediction evaluation subsets:

| Partition | Cases | Positive | Negative |
|---|---:|---:|---:|
| purged_overlap | 497 | 268 | 229 |
| test | 2001 | 668 | 1333 |
| train | 5783 | 1320 | 4463 |
| validation | 1752 | 496 | 1256 |

## ML-ready design (no fitted pipeline)

- Unit: one declaration case at its second recorded event. Case ID is a join/group key, never a feature. prediction_timestamp is evaluation metadata, not an absolute-time model feature.
- Numerical candidates: observed prefix elapsed hours and UTC calendar month/weekday/hour (calendar encoding to be chosen using training only). Prefix length two is constant and dropped.
- Categorical candidates: first/current activity, exact two-activity prefix, event resource and role at the landmark. Preserve missing event categories as Unknown; distinguish recorded UNDEFINED/MISSING strings from null. Unknown categories at evaluation must be handled by a train-fitted encoder.
- All final trace attributes are excluded: Amount, BudgetNumber, DeclarationNumber and trace identifiers. They are constant within a case in XES, but the log has no as-of version history proving availability at the prediction point. Event resource/role are candidates conditional on verifying ingestion-time availability; perform an activity/time-only sensitivity analysis.
- Exclude final duration, future count, final variant, future repeats/activities/outcome, IDs and source row as predictors. Full outcomes are permitted only in separate retrospective labels and split-purging metadata. prediction_prefix returns no final case attributes or outcomes.
- Retain valid, nonempty canonical cases. Second-event eligibility is determined when that event arrives; singleton cases never reach it. Reject invalid required fields/timestamps/provenance rather than impute them. Source loader retains the existing validated data-quality contract.
- Learned imputers, encoders, scalers, selection and tuning fit only training partitions. No feature transformer or model is fitted on Day 6. Candidate features and metadata exist in memory; no unnecessary duplicate ML dataset is saved.

## Temporal evaluation proposal

Validation starts 2018-06-27T09:27:50+00:00; test starts 2018-10-12T13:06:56+00:00. Initial boundaries are at 60% and 80% of ordered eligible prediction timestamps. Equal timestamps remain together. Train observed endpoints reaching validation and validation endpoints reaching test are purged, including equality. 520 cases are purged; this reduces future-label overlap but biases toward shorter cases, so report their distribution explicitly.

Train labels are only observationally mature before validation, not certified true completion. Deployment requires outcome-availability policy and censoring treatment. Unrestricted random case splits are unsuitable for the intended historical-to-future assessment. Use the frozen chronological holdout and, later, rolling-origin sensitivity checks with the same endpoint-purging rule. Standard TimeSeriesSplit alone does not implement overlapping case-label purging or irregular-event eligibility.

For Day 7, proposed evaluation includes prevalence/majority and elapsed-prefix baselines, interpretable logistic/tree candidates, PR-AUC, ROC-AUC, precision/recall at a train/validation-chosen threshold, calibration and subgroup/error review. Do not use held-out outcomes for hyperparameter/feature decisions. Report no performance metric before fitting and evaluation. General leakage guidance: [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html); chronological split reference: [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html). Scikit-learn was not added or used for fitting here.

## Research workflow and limitations

Process mining describes routes, repeated submissions and long-tail recorded spans. Future ML estimates a longer recorded-span label at an early landmark. Possible human-reviewed investigations include reviewing repeated submission documentation or prioritizing a case review; no benefit or causal effect is established by these associations.

Later simulation scope must be reconsidered around descriptive span/path scenarios with explicit assumptions and sensitivity bounds. Completion-only timestamps cannot identify service durations, queue times, resource capacity or the effect of removing approvals. A credible operational improvement simulation needs additional timing/capacity/intervention evidence. The selected label is suitable for an observational early-risk thesis experiment, but is not itself a validated causal optimization objective. No recommendation engine, LLM or simulation was implemented.

Reproduce the small CSV/JSON artifacts with `python -B scripts/run_day6.py`. Original XES/Parquet and historical outputs remain unchanged. Numerical regression and future-mutation tests verify label boundaries, eligibility, prefix ordering and holdout-threshold independence.
