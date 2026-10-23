"""Historical candidate investigation and leakage-aware prediction design; no model fitting."""
import math
import pandas as pd
from smartbpm.dashboard import C, prepare_dashboard
from smartbpm.process_mining import ordered_events, variant_performance, repetition_performance


def duration_labels(days, threshold):
    """Strictly greater than a frozen research threshold, measured in elapsed days."""
    values = pd.to_numeric(days, errors="raise")
    if not math.isfinite(threshold) or threshold < 0 or values.isna().any() or not values.map(math.isfinite).all() or values.lt(0).any():
        raise ValueError("Durations and threshold must be finite nonnegative days")
    return values.gt(threshold).astype("int8")


def prediction_prefix(events, count=1, activity=None):
    """One row/case at kth event or first named activity; never read later feature values.

    Event position uses canonical timestamp/source ordering. Simultaneous later rows
    are not included: this assumes an online source-order-equivalent ingestion stream.
    """
    if not isinstance(count, int) or count < 1:
        raise ValueError("Prefix count must be a positive integer")
    frame = ordered_events(events)
    frame["prefix_position"] = frame.groupby(C.case).cumcount() + 1
    if activity is not None:
        selected = frame.loc[frame[C.activity].eq(activity)].groupby(C.case, sort=True).head(1)
    else:
        selected = frame.loc[frame.prefix_position.eq(count)]
    first = frame.groupby(C.case)[C.timestamp].first()
    result = selected[[C.case, C.timestamp, C.activity, "prefix_position", "_source_order"]].rename(columns={C.timestamp:"prediction_timestamp", C.activity:"current_activity"}).copy()
    # Only event-scoped attributes, not final trace attributes, enter this design.
    for name in (C.resource, "org:role"):
        result[name] = selected[name].fillna("Unknown").astype(str).values if name in selected else "Unknown"
    result["prefix_elapsed_hours"] = (result.prediction_timestamp - result[C.case].map(first)).dt.total_seconds()/3600
    result["utc_month"] = result.prediction_timestamp.dt.month
    result["utc_weekday"] = result.prediction_timestamp.dt.dayofweek
    result["utc_hour"] = result.prediction_timestamp.dt.hour
    # Extract history only up to each selected row, including for a named landmark.
    boundaries = dict(zip(result[C.case], result.prefix_position))
    prefix = frame.loc[frame.prefix_position.le(frame[C.case].map(boundaries))]
    positions = prefix.groupby(C.case, sort=True).indices
    values = prefix[C.activity].to_numpy()
    histories = pd.Series({key:tuple(values[indices]) for key,indices in positions.items()})
    result["activity_prefix"] = result[C.case].map(histories)
    result["first_activity"] = result.activity_prefix.map(lambda value:value[0])
    return result.reset_index(drop=True)


def temporal_design(cases, prefix):
    """Group equal prediction timestamps; purge labels crossing next split boundary."""
    rows = prefix[[C.case,"prediction_timestamp"]].merge(cases[[C.case,"end_timestamp","elapsed_days"]],on=C.case,validate="one_to_one")
    if len(rows)<5:
        raise ValueError("At least five eligible cases required for temporal design")
    times = rows.prediction_timestamp.sort_values().reset_index(drop=True)
    validation_start = times.iloc[int(len(times)*.6)]
    test_start = times.iloc[int(len(times)*.8)]
    if validation_start >= test_start or times.iloc[0] >= validation_start:
        raise ValueError("Insufficient distinct prediction timestamps for temporal splits")
    rows["split"] = "test"
    rows.loc[rows.prediction_timestamp.lt(test_start),"split"] = "validation"
    rows.loc[rows.prediction_timestamp.lt(validation_start),"split"] = "train"
    purge = (rows.split.eq("train") & rows.end_timestamp.ge(validation_start)) | (rows.split.eq("validation") & rows.end_timestamp.ge(test_start))
    rows.loc[purge,"split"] = "purged_overlap"
    training = rows.loc[rows.split.eq("train"),"elapsed_days"]
    if training.empty:
        raise ValueError("No mature training labels before validation boundary")
    threshold = float(training.quantile(.75))
    rows["target_long_observed"] = duration_labels(rows.elapsed_days, threshold)
    return rows, {"validation_start":validation_start.isoformat(),"test_start":test_start.isoformat(),"threshold_days":threshold,
                  "threshold_source":"75th percentile of training-only observed durations after overlap purging; linear interpolation",
                  "split_counts":rows.split.value_counts().to_dict()}


def investigate(events, tables=None):
    if events.empty:
        raise ValueError("Investigation requires a nonempty cohort")
    if tables is None:
        _,tables = prepare_dashboard(ordered_events(events))
    cases = tables["case_summary"]
    days = cases.elapsed_days
    stats = {"cases":len(cases),"mean_days":float(days.mean()),"median_days":float(days.median()),
             **{f"p{int(q*100)}_days":float(days.quantile(q)) for q in (.75,.9,.95)}}
    thresholds = pd.DataFrame([{"threshold_days":n,"cases_above":int(days.gt(n).sum()),"share_above":float(days.gt(n).mean())} for n in (7,14,21,30,float(days.quantile(.75)),float(days.quantile(.9)))])
    flags,groups = repetition_performance(cases,tables["repeated_activities_by_case"])
    variants = variant_performance(cases,tables["process_variants"])
    repeated_by_variant=cases.assign(repeated=cases.repeated_activity_types.gt(0)).groupby("variant_id").repeated.sum().rename("repeated_cases")
    variants=variants.join(repeated_by_variant,on="variant_id")
    rare_ids = variants.loc[variants.case_count.lt(10),"variant_id"]
    rare = cases.variant_id.isin(rare_ids)
    rare_groups = cases.assign(group=rare.map({True:"Rare variant (<10 cases)",False:"Other variants"})).groupby("group").elapsed_days.agg(cases="size",median_days="median",mean_days="mean").reset_index()
    stats.update({"repeated_cases":int(cases.repeated_activity_types.gt(0).sum()),"repeated_share":float(cases.repeated_activity_types.gt(0).mean()),
                  "variants":len(variants),"rare_variants":len(rare_ids),"rare_variant_cases":int(rare.sum()),"single_event_cases":int(cases.event_count.eq(1).sum()),
                  "nonpayment_endpoints":int(cases.end_activity.ne("Payment Handled").sum())})
    points=[]
    for title,kwargs in (("First recorded event",{"count":1}),("Second recorded event",{"count":2}),("First submission",{"activity":"Declaration SUBMITTED by EMPLOYEE"})):
        prefix=prediction_prefix(events,**kwargs)
        outcomes=prefix.merge(cases[[C.case,"end_timestamp"]],on=C.case)
        points.append({"prediction_point":title,"eligible_cases":len(prefix),"excluded_cases":len(cases)-len(prefix),
                       "at_last_observed_timestamp":int(outcomes.prediction_timestamp.eq(outcomes.end_timestamp).sum()),
                       "median_prefix_events":float(prefix.prefix_position.median()) if len(prefix) else None,
                       "median_elapsed_hours":float(prefix.prefix_elapsed_hours.median()) if len(prefix) else None})
    return stats,{"thresholds":thresholds,"repetition_groups":groups,"repeated_activities":tables["repeated_activity_summary"],"variants":variants,"rare_groups":rare_groups,"prediction_points":pd.DataFrame(points)}


def target_definition(events, tables=None):
    if tables is None:
        _,tables=prepare_dashboard(ordered_events(events))
    prefix=prediction_prefix(events, count=2)
    labels,design=temporal_design(tables["case_summary"],prefix)
    known = prefix.set_index(C.case).prefix_elapsed_hours.gt(design["threshold_days"]*24)
    labels["already_above_threshold_at_prediction"] = labels[C.case].map(known).astype(bool)
    distributions=[]
    for name,group in [("all_eligible",labels),*list(labels.groupby("split",sort=True))]:
        distributions.append({"cohort":name,"cases":len(group),"positive":int(group.target_long_observed.sum()),"negative":int(group.target_long_observed.eq(0).sum()),"positive_share":float(group.target_long_observed.mean())})
    unknown_balance=[]
    for name,group in labels.loc[~labels.already_above_threshold_at_prediction].groupby("split",sort=True):
        unknown_balance.append({"split":name,"cases":len(group),"positive":int(group.target_long_observed.sum()),"negative":int(group.target_long_observed.eq(0).sum())})
    return {"target":"long_observed_case_elapsed_duration","status":"Frozen Day 6 target definition; trained-model results reported separately",
            "formula":"y = 1[(last observed timestamp - first observed timestamp)/86400 seconds > threshold_days]",
            "units":"days","prediction_point":"Immediately after second recorded event in canonical timestamp/source order",
            "eligible_cases":len(prefix),"excluded_single_event_cases":int(tables["case_summary"].event_count.eq(1).sum()),
            "already_above_threshold_cases":int(labels.already_above_threshold_at_prediction.sum()),
            "unknown_at_prediction_cases":int((~labels.already_above_threshold_at_prediction).sum()),"label_scope":"Recorded span only, not true completion time or an official SLA",
            **design,"class_balance":distributions,"unknown_label_class_balance":unknown_balance,
            "candidate_features":["current_activity","org:resource","org:role","utc_month","utc_weekday","utc_hour","prefix_elapsed_hours","first_activity"],
            "prefix_features":"Exact first-two-activity prefix, first/current activity, observed prefix elapsed hours; prefix length 2 is constant and dropped",
            "excluded_features":["case:Amount","case:BudgetNumber","case:DeclarationNumber","case:id","case identifier","final elapsed duration","future event count","final variant","final outcome","future activities","absolute timestamp and source row as model features"],
            "attribute_availability":"Final XES trace attributes have no as-of version history; availability at the prediction point cannot be established. Exclude them. Event attributes require ingestion-time availability confirmation before deployment.",
            "evaluation":"Chronological 60/20/20 by prediction timestamp, equal timestamps stay together; purge train/validation observed endpoints reaching next split boundary. Freeze threshold on remaining training only; fit encoders/imputers on train only. Report purged-case bias and endpoint sensitivity. No case crosses feature partitions. Report already-above-threshold cases separately; future predictive metrics must also exclude these known positives without refitting the frozen threshold.",
            "limitations":["Unknown censoring: low observed span is not proof of prompt true completion","Second-event eligibility excludes 134 singleton traces in this dataset; report this selection bias","First-event features have almost no variation; second-event features are richer but may still be weak","No causal intervention benefit follows from observational associations","Future simulation must use explicit scenario assumptions; service/queue/capacity cannot be identified here"]},labels


def candidate_comparison(stats):
    return pd.DataFrame([
        {"candidate":"Long observed duration","selected":True,"support":f"Mean {stats['mean_days']:.3f} days; p95 {stats['p95_days']:.3f}","relevance":"Timely human case review","measurability":"UTC recorded span; censoring limits validity","label_reliability":"Observed-span label available; not true completion","early_feasibility":"Second event covers 10,366 cases; first-event attributes nearly constant","leakage":"Exclude final duration/history; train-only threshold","balance":"Research p75 training threshold targets about 25% training positives","interpretability":"Binary target suitable for simple interpretable baselines","recommendations":"Review protocols only; effects unproven","simulation":"Descriptive span scenarios only; no identified service/capacity model","timeline":"Feasible next-stage baseline"},
        {"candidate":"Future repeated activity","selected":False,"support":f"{stats['repeated_cases']} cases ({stats['repeated_share']:.2%})","relevance":"Understand resubmission/review","measurability":"Repeated exact label","label_reliability":"May be legitimate; censoring hides later repeats","early_feasibility":"First/second-event prediction possible","leakage":"Final counts/variant reveal outcome","balance":"About 9.7% full-log positives","interpretability":"Interpretable but heterogeneous causes","recommendations":"Need contextual validation","simulation":"Cannot assume repetition is avoidable","timeline":"Possible secondary target"},
        {"candidate":"Rare final variant","selected":False,"support":f"{stats['rare_variants']} variants have fewer than 10 cases; {stats['rare_variant_cases']} cases","relevance":"Review uncommon paths","measurability":"Exact sequence membership","label_reliability":"Rare is sample-dependent, not an error","early_feasibility":"Unseen future sequences difficult","leakage":"Full sequence leaks label; rarity must be train-defined","balance":"Sparse heterogeneous groups","interpretability":"Weak operational meaning","recommendations":"Human investigation only","simulation":"Rare routes too sparse for reliable calibration","timeline":"Defer"}])
