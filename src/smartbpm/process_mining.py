"""Observed directly-follows discovery, variant performance and repetition associations.

No service times, queue times, BPMN gateways or causal effects are inferred.
"""
import numpy as np
import pandas as pd
from pm4py.algo.discovery.dfg.adapters.pandas.df_statistics import get_dfg_graph
from smartbpm.dataset import validate_events
from smartbpm.preprocessing import Columns

C = Columns()
TRANSITION_COLUMNS = ["source", "target", "frequency", "case_count", "median_hours", "mean_hours", "p90_hours", "p95_hours", "max_hours", "zero_gap_occurrences"]


def ordered_events(events):
    """Require source provenance; canonical order is case/UTC time/source row."""
    required = [C.case, C.activity, C.timestamp, "_source_order"]
    missing = [name for name in required if name not in events]
    if missing:
        raise ValueError(f"Missing mining columns: {missing}")
    if events.empty:
        return events.copy()
    validate_events(events)
    for name in (C.case, C.activity):
        if not events[name].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError("Case and activity labels must be nonblank strings")
    if not isinstance(events[C.timestamp].dtype, pd.DatetimeTZDtype):
        raise ValueError("Mining timestamps must be timezone-aware datetimes")
    source = events["_source_order"]
    if not pd.api.types.is_integer_dtype(source) or source.isna().any() or not source.is_unique or source.lt(0).any():
        raise ValueError("Mining requires unique nonnegative source-order provenance")
    result = events.copy()
    result[C.timestamp] = result[C.timestamp].dt.tz_convert("UTC")
    return result.sort_values([C.case, C.timestamp, "_source_order"], kind="stable").reset_index(drop=True)


def discover_transitions(events):
    """PM4Py frequency DFG plus elapsed gaps on the same consecutive records.

    Use PM4Py's pandas DFG backend with sorting disabled AFTER canonical sorting.
    Supplying start_timestamp_key avoids the backend adding a start-time column.
    Counts are cross-checked against vectorized adjacency; no event is removed.
    """
    frame = ordered_events(events)
    if frame.empty:
        return pd.DataFrame(columns=TRANSITION_COLUMNS), {"events": 0, "cases": 0, "activities": 0, "transition_occurrences": 0, "distinct_transitions": 0, "starts": {}, "ends": {}}
    dfg = get_dfg_graph(frame[[C.case, C.activity, C.timestamp]].copy(),
                        activity_key=C.activity, case_id_glue=C.case,
                        timestamp_key=C.timestamp, start_timestamp_key=C.timestamp,
                        sort_caseid_required=False, sort_timestamp_along_case_id=False)
    grouped = frame.groupby(C.case, sort=True)
    next_activity = grouped[C.activity].shift(-1)
    next_stamp = grouped[C.timestamp].shift(-1)
    mask = next_activity.notna()
    pairs = pd.DataFrame({"source": frame.loc[mask, C.activity], "target": next_activity[mask],
                          "case": frame.loc[mask, C.case],
                          "hours": (next_stamp[mask] - frame.loc[mask, C.timestamp]).dt.total_seconds() / 3600})
    if pairs.empty:
        transitions = pd.DataFrame(columns=TRANSITION_COLUMNS)
    else:
        pair_groups = pairs.groupby(["source", "target"], sort=True)
        transitions = pair_groups.agg(frequency=("hours", "size"), case_count=("case", "nunique"),
                                      median_hours=("hours", "median"), mean_hours=("hours", "mean"),
                                      max_hours=("hours", "max")).reset_index()
        quantiles = pair_groups.hours.quantile([.9, .95]).unstack().rename(columns={.9: "p90_hours", .95: "p95_hours"})
        zero = pairs.assign(zero=pairs.hours.eq(0)).groupby(["source", "target"]).zero.sum().rename("zero_gap_occurrences")
        transitions = transitions.join(quantiles, on=["source", "target"]).join(zero, on=["source", "target"])
        observed = {(row.source, row.target): int(row.frequency) for row in transitions.itertuples()}
        if observed != dict(dfg):
            raise RuntimeError("PM4Py DFG counts do not match canonically ordered adjacency")
        transitions["frequency"] = [int(dfg[(s, t)]) for s, t in zip(transitions.source, transitions.target)]
        transitions = transitions[TRANSITION_COLUMNS].sort_values(["frequency", "source", "target"], ascending=[False, True, True]).reset_index(drop=True)
    summary = {"events": len(frame), "cases": int(frame[C.case].nunique()),
               "activities": int(frame[C.activity].nunique()), "distinct_transitions": len(transitions),
               "transition_occurrences": int(transitions.frequency.sum()) if len(transitions) else 0,
               "starts": grouped[C.activity].first().value_counts().to_dict(),
               "ends": grouped[C.activity].last().value_counts().to_dict(),
               "method": "PM4Py frequency directly-follows pandas backend, on case/timestamp/source-order sorted events",
               "interpretation": "Edges connect consecutive recorded events within a case. Gaps are elapsed time, not measured service or queue waiting time. No gateways or concurrency semantics inferred."}
    if summary["transition_occurrences"] != summary["events"] - summary["cases"]:
        raise RuntimeError("DFG adjacency conservation failed")
    return transitions, summary


def select_transitions(transitions, minimum=1, maximum=20, focus=()):
    """Display-only selection from real edges; never drop events or bridge paths."""
    if minimum < 1 or maximum < 1:
        raise ValueError("Minimum frequency and maximum edge count must be positive")
    selected = transitions.loc[transitions.frequency.ge(minimum)]
    if focus:
        selected = selected.loc[selected.source.isin(focus) | selected.target.isin(focus)]
    return selected.sort_values(["frequency", "source", "target"], ascending=[False, True, True]).head(maximum).copy()


def variant_performance(cases, variants):
    """One duration observation per case; share denominator is the selected cohort."""
    if cases.empty:
        return variants.assign(median_days=pd.Series(dtype=float), p90_days=pd.Series(dtype=float),
                               p95_days=pd.Series(dtype=float), mean_days=pd.Series(dtype=float), min_days=pd.Series(dtype=float), max_days=pd.Series(dtype=float))
    grouped = cases.groupby("variant_id").elapsed_days
    stats = grouped.agg(median_days="median", mean_days="mean", min_days="min", max_days="max")
    quantiles = grouped.quantile([.9, .95]).unstack().rename(columns={.9: "p90_days", .95: "p95_days"})
    return variants.merge(stats.join(quantiles), on="variant_id", how="left", validate="one_to_one")


def repetition_performance(cases, repeated):
    """Lexical approval/rejection groups overlap; association does not imply cause."""
    labeled = cases.copy()
    labeled["repetition_group"] = np.where(labeled.repeated_activity_types.gt(0), "Repeated activity", "No repeated activity")
    for pattern, name in ((r"(?:^|[_ ])APPROVED(?: |$)", "repeated_approval"), (r"(?:^|[_ ])REJECTED(?: |$)", "repeated_rejection")):
        ids = repeated.loc[repeated[C.activity].str.contains(pattern, regex=True, na=False), C.case]
        labeled[name] = labeled[C.case].isin(ids)
    rows = []
    for name, mask in (("No repeated activity", labeled.repeated_activity_types.eq(0)),
                        ("Repeated activity", labeled.repeated_activity_types.gt(0)),
                        ("Repeated approval (overlapping subset)", labeled.repeated_approval),
                        ("Repeated rejection (overlapping subset)", labeled.repeated_rejection)):
        durations = labeled.loc[mask, "elapsed_days"]
        rows.append({"group": name, "cases": len(durations),
                     "median_days": float(durations.median()) if len(durations) else None,
                     "mean_days": float(durations.mean()) if len(durations) else None,
                     "p90_days": float(durations.quantile(.9)) if len(durations) else None,
                     "p95_days": float(durations.quantile(.95)) if len(durations) else None})
    return labeled, pd.DataFrame(rows)
