"""Observed process statistics; no completion or processing-time inference."""
import json
import pandas as pd
from smartbpm.preprocessing import Columns, descriptive_stats


def describe_process(events, columns=Columns()):
    """Input must be the ordered UTC output of preprocess_events."""
    grouped = events.groupby(columns.case, sort=True)
    cases = grouped.agg(event_count=(columns.activity, "size"),
                        start_timestamp=(columns.timestamp, "min"),
                        end_timestamp=(columns.timestamp, "max"),
                        start_activity=(columns.activity, "first"),
                        end_activity=(columns.activity, "last"))
    cases["elapsed_days"] = (cases.end_timestamp - cases.start_timestamp).dt.total_seconds() / 86400
    q1, q3 = cases.event_count.quantile([.25, .75])
    cases["short_trace_iqr_flag"] = cases.event_count.lt(q1 - 1.5 * (q3 - q1))
    cases["long_trace_iqr_flag"] = cases.event_count.gt(q3 + 1.5 * (q3 - q1))
    cases["not_ending_in_payment_flag"] = cases.end_activity.ne("Payment Handled")
    cases["timestamp_tie_flag"] = events.duplicated([columns.case, columns.timestamp], keep=False).groupby(events[columns.case]).any().reindex(cases.index)
    # Avoid constructing one Arrow-backed Series for each case.
    activity_values = events[columns.activity].to_numpy()
    positions = grouped.indices
    sequences = pd.Series([tuple(activity_values[positions[key]]) for key in cases.index],
                          index=cases.index, dtype=object)
    variants = sequences.value_counts().rename_axis("sequence").reset_index(name="case_count")
    variants["sequence"] = variants["sequence"].map(lambda value: json.dumps(value, ensure_ascii=False))
    variants = variants.sort_values(["case_count", "sequence"], ascending=[False, True]).reset_index(drop=True)
    variants.insert(0, "variant_id", [f"V{i + 1:04}" for i in range(len(variants))])
    variants["case_share"] = variants.case_count / len(cases)
    variant_ids = {tuple(json.loads(sequence)): variant_id for sequence, variant_id in zip(variants.sequence, variants.variant_id)}
    cases["variant_id"] = sequences.map(variant_ids.__getitem__)
    counts = events.groupby([columns.case, columns.activity]).size().rename("occurrences").reset_index()
    repeats = counts[counts.occurrences.gt(1)].copy()
    repeats["excess_occurrences"] = repeats.occurrences - 1
    cases["repeated_activity_types"] = repeats.groupby(columns.case).size().reindex(cases.index, fill_value=0)
    repeat_summary = repeats.groupby(columns.activity).agg(cases=(columns.case, "nunique"), excess_occurrences=("excess_occurrences", "sum"))
    repeat_summary = repeat_summary.sort_values(["cases", "excess_occurrences"], ascending=False)
    adjacent = events[columns.case].eq(events[columns.case].shift()) & events[columns.activity].eq(events[columns.activity].shift())
    activity = events[columns.activity].value_counts().rename_axis("activity").reset_index(name="event_count")
    resources = (events[columns.resource].value_counts(dropna=False).rename_axis("resource").reset_index(name="event_count")
                 if columns.resource in events else pd.DataFrame(columns=["resource", "event_count"]))
    starts = cases.start_activity.value_counts().rename_axis("activity").reset_index(name="case_count")
    ends = cases.end_activity.value_counts().rename_axis("activity").reset_index(name="case_count")
    duration = descriptive_stats(cases.elapsed_days, percentiles=[.05, .25, .5, .75, .9, .95, .99])
    summary = {"total_cases": len(cases), "total_events": len(events), "total_activities": len(activity),
               "variant_count": len(variants), "duration_days": duration,
               "events_per_case": descriptive_stats(cases.event_count),
               "activity_frequency": dict(zip(activity.activity, activity.event_count)),
               "common_starts": dict(zip(starts.activity, starts.case_count)),
               "common_ends": dict(zip(ends.activity, ends.case_count)),
               "top_variants": variants.head(10).to_dict(orient="records"),
               "cases_with_repeated_activities": int(cases.repeated_activity_types.gt(0).sum()),
               "adjacent_repeated_activity_events": int(adjacent.sum()),
               "repeated_activity_patterns": repeat_summary.reset_index().to_dict(orient="records"),
               "endpoint_observations": {"cases_not_ending_in_Payment_Handled": int(cases.end_activity.ne("Payment Handled").sum()),
                                         "note": "Dataset-specific descriptive flag, not proof of error or incompleteness. Rejection, alternative endings or observation boundaries may matter."},
               "interpretation": ["Case elapsed duration is last minus first observed timestamp, not active processing time.",
                                  "Unknown pre-log or post-log activity can censor observed case durations.",
                                  "Variants and endpoints use chronological order; timestamp ties retain XES order.",
                                  "Rare variants, long/short traces and repetitions are retained as observed behavior."]}
    tables = {"case_summary": cases.reset_index(), "activity_frequency": activity,
              "resource_frequency": resources, "process_variants": variants,
              "repeated_activities_by_case": repeats, "repeated_activity_summary": repeat_summary.reset_index(),
              "starting_activities": starts, "ending_activities": ends,
              "duration_distribution": pd.Series(duration, name="elapsed_days").rename_axis("statistic").reset_index()}
    return summary, tables


def save_charts(tables, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []

    def save(fig, name):
        fig.tight_layout()
        path = directory / f"{name}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)

    for table, label, value in [("activity_frequency", "activity", "event_count"),
                                 ("resource_frequency", "resource", "event_count"),
                                 ("starting_activities", "activity", "case_count"),
                                 ("ending_activities", "activity", "case_count")]:
        frame = tables[table].head(20).iloc[::-1]
        fig, ax = plt.subplots(figsize=(11, 7))
        ax.barh(frame[label].astype(str), frame[value])
        ax.set(xlabel=value.replace("_", " ").capitalize(), title=table.replace("_", " ").capitalize())
        save(fig, table)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(tables["case_summary"].elapsed_days, bins=50, edgecolor="white")
    ax.set(xlabel="Observed elapsed days (not active processing time)", ylabel="Cases", title="Observed case duration distribution")
    save(fig, "case_duration_distribution")
    lengths = tables["case_summary"].event_count.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(lengths.index, lengths.values)
    ax.set(xlabel="Events per case", ylabel="Cases", title="Trace length distribution")
    save(fig, "events_per_case")
    top = tables["process_variants"].head(10)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(top.variant_id, top.case_count)
    ax.set(xlabel="Variant ID (sequences in process_variants.csv)", ylabel="Cases", title="Ten most common observed variants")
    save(fig, "top_process_variants")
    return paths


