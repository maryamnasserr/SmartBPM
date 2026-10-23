"""Read-only dashboard data loading and complete-case cohort selection."""
import math
from pathlib import Path
import pandas as pd
from smartbpm.exploration import describe_process
from smartbpm.preprocessing import Columns, quality_report

C = Columns()


def load_dashboard_events(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Processed dataset missing. Run python scripts/run_day2.py first.")
    frame = pd.read_parquet(path)
    required = [C.case, C.activity, C.timestamp, C.resource, "_source_order"]
    missing = [name for name in required if name not in frame]
    if missing:
        raise ValueError(f"Processed dataset is missing columns: {missing}")
    provenance = frame["_source_order"]
    if not pd.api.types.is_integer_dtype(provenance) or provenance.isna().any() or not provenance.is_unique or provenance.lt(0).any():
        raise ValueError("Source-order provenance must be unique nonnegative integers")
    quality = quality_report(frame.drop(columns="_source_order"))
    if quality["confirmed_defects"]:
        raise ValueError("Invalid processed data: " + "; ".join(quality["confirmed_defects"]))
    if not isinstance(frame[C.timestamp].dtype, pd.DatetimeTZDtype):
        raise ValueError("Processed timestamps must be timezone-aware datetimes")
    frame[C.timestamp] = frame[C.timestamp].dt.tz_convert("UTC")
    return frame.sort_values([C.case, C.timestamp, "_source_order"], kind="stable").reset_index(drop=True)


def prepare_dashboard(events):
    """Reuse Day 2 analytics; empty cohorts intentionally have no analytical tables."""
    if events.empty:
        return {"total_cases": 0, "total_events": 0, "total_activities": 0,
                "variant_count": 0, "duration_days": {"50%": None},
                "cases_with_repeated_activities": 0}, {}
    return describe_process(events)


def filter_cases(events, cases, *, activities=None, resources=None,
                 start_date=None, end_date=None, duration_range=None):
    """OR within categories; AND across categories. None=all, []=no matches.

    Activity/resource matches may occur on different events of the same case.
    Date bounds are inclusive UTC case-start dates. Entire histories are returned.
    """
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Start date must not follow end date")
    if duration_range is not None:
        lower, upper = duration_range
        if not math.isfinite(lower) or not math.isfinite(upper) or lower < 0 or upper < lower:
            raise ValueError("Invalid duration range")
    selected = cases
    if start_date is not None:
        selected = selected[selected.start_timestamp >= pd.Timestamp(start_date, tz="UTC")]
    if end_date is not None:
        selected = selected[selected.start_timestamp < pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)]
    if duration_range is not None:
        selected = selected[selected.elapsed_days.between(*duration_range, inclusive="both")]
    for column, values in ((C.activity, activities), (C.resource, resources)):
        if values is not None:
            matching = events.loc[events[column].isin(values), C.case].unique()
            selected = selected[selected[C.case].isin(matching)]
    return events.loc[events[C.case].isin(selected[C.case])].copy()


def csv_bytes(frame):
    """Export exactly the supplied analytical table, without its DataFrame index."""
    return frame.to_csv(index=False).encode('utf-8')

