"""Read-only XES loading and reproducible schema profiling."""
from pathlib import Path
from copy import deepcopy
import hashlib
import pandas as pd
import pm4py

REQUIRED = ("case:concept:name", "concept:name", "time:timestamp")


def validate_events(frame):
    if frame.empty:
        raise ValueError("Event log contains no events")
    absent = [name for name in REQUIRED if name not in frame.columns]
    if absent:
        raise ValueError(f"Missing required event fields: {absent}")
    if frame[list(REQUIRED)].isna().any().any():
        raise ValueError("Required event fields contain missing values")
    for name in REQUIRED[:2]:
        if frame[name].astype(str).str.strip().eq("").any():
            raise ValueError(f"Required field is blank: {name}")
    if pd.to_datetime(frame["time:timestamp"], utc=True, errors="coerce").isna().any():
        raise ValueError("Event timestamps contain invalid values")


def load_event_log(path, *, validate=True):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Place the XES dataset at {path}")
    with path.open("rb") as source:
        if not source.read(1):
            raise ValueError(f"Dataset is empty: {path}")
    try:
        log = pm4py.read_xes(str(path), return_legacy_log_object=True, show_progress_bar=False)
        frame = pm4py.convert_to_dataframe(deepcopy(log))
    except Exception as exc:
        raise ValueError(f"Cannot parse XES dataset {path}: {exc}") from exc
    if validate:
        validate_events(frame)
    return log, frame


def profile_dataset(path):
    path = Path(path)
    log, frame = load_event_log(path)
    stamps = pd.to_datetime(frame["time:timestamp"], utc=True)
    event_attrs = sorted({key for trace in log for event in trace for key in event})
    trace_attrs = sorted({key for trace in log for key in trace.attributes})
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {
        "source": str(path.resolve()), "source_sha256": digest,
        "source_bytes": path.stat().st_size,
        "event_count": len(frame), "case_count": int(frame["case:concept:name"].nunique()),
        "trace_count": len(log), "empty_trace_count": sum(not trace for trace in log),
        "activity_count": int(frame["concept:name"].nunique()),
        "activities": frame["concept:name"].value_counts().to_dict(),
        "timestamp_range_utc": {"min": stamps.min().isoformat(), "max": stamps.max().isoformat()},
        "schema": {name: str(dtype) for name, dtype in frame.dtypes.items()},
        "event_attributes": event_attrs, "trace_attributes": trace_attrs,
        "missing_values": {name: int(count) for name, count in frame.isna().sum().items()},
        "missing_event_attributes": {key: sum(key not in event for trace in log for event in trace) for key in event_attrs},
        "missing_trace_attributes": {key: sum(key not in trace.attributes for trace in log) for key in trace_attrs},
        "sample": __import__("json").loads(frame.head(5).to_json(orient="records", date_format="iso")),
        "preprocessing": ["No records excluded, imputed, deduplicated or sorted.",
                          "PM4Py flattens trace attributes with case: prefix.",
                          "Timestamp summary expressed in UTC; source file unchanged.",
                          "No processing durations, capacities or SLA thresholds inferred."],
    }
