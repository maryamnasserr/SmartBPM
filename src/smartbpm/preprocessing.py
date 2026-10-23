"""Non-destructive quality checks and deterministic analytical event ordering."""
from dataclasses import asdict, dataclass
from collections import Counter
from datetime import datetime
import xml.etree.ElementTree as ET
from numbers import Real

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Columns:
    case: str = "case:concept:name"
    activity: str = "concept:name"
    timestamp: str = "time:timestamp"
    event_id: str = "id"
    resource: str = "org:resource"


def parsed_timestamps(series):
    """Reject ambiguous naive timestamps rather than silently assigning a timezone."""
    parsed = []
    naive = 0
    offsets = Counter()
    for value in series:
        try:
            if pd.isna(value) or isinstance(value, (int, float, bool)):
                raise ValueError("Missing or non-date timestamp")
            stamp = pd.Timestamp(value)
            if stamp.tzinfo is None:
                naive += 1
                parsed.append(pd.NaT)
                continue
            offsets[str(stamp.utcoffset())] += 1
            parsed.append(stamp.tz_convert("UTC"))
        except (ValueError, TypeError, OverflowError):
            parsed.append(pd.NaT)
    return pd.Series(pd.to_datetime(parsed, utc=True), index=series.index), naive, dict(offsets)


def inspect_xes_source(path):
    """Audit date offsets and attribute XML types before PM4Py normalizes values."""
    offsets, types = Counter(), Counter()
    naive = invalid = 0
    for _, element in ET.iterparse(path, events=("end",)):
        tag = element.tag.rsplit("}", 1)[-1]
        key = element.get("key")
        if key:
            types[f"{key}|{tag}"] += 1
        if key == "time:timestamp":
            try:
                stamp = datetime.fromisoformat(element.get("value", "").replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    naive += 1
                else:
                    offsets[str(stamp.utcoffset())] += 1
            except ValueError:
                invalid += 1
        element.clear()
    return {"timestamp_offsets": dict(offsets), "naive_timestamps": naive,
            "invalid_timestamps": invalid, "attribute_xml_types": dict(sorted(types.items())),
            "note": "Different UTC offsets can reflect daylight saving; offsets alone do not identify a named timezone."}


def descriptive_stats(series, **kwargs):
    return {key: None if pd.isna(value) else float(value)
            for key, value in series.describe(**kwargs).items()}


def case_attribute_conflicts(frame, columns=Columns()):
    result = {}
    for name in frame.columns:
        if name.startswith("case:") and name != columns.case:
            distinct = frame.groupby(columns.case, dropna=False)[name].nunique(dropna=False)
            result[name] = {"conflicting_cases": int(distinct.gt(1).sum()),
                            "example_case_ids": distinct[distinct.gt(1)].index.astype(str).tolist()[:10]}
    return result


def quality_report(frame, columns=Columns()):
    required = [columns.case, columns.activity, columns.timestamp]
    missing_columns = [name for name in required if name not in frame]
    report = {"column_mapping": asdict(columns), "event_count": len(frame),
              "schema": {name: str(dtype) for name, dtype in frame.dtypes.items()},
              "missing_values": {name: int(n) for name, n in frame.isna().sum().items()},
              "missing_required_columns": missing_columns, "confirmed_defects": [],
              "interpretation": "Repetitions, short/long cases and uncommon endpoints are observations, not automatic errors."}
    if missing_columns or frame.empty:
        report["confirmed_defects"].append("Empty log or missing required columns")
        return report
    required_invalid = {}
    for name in (columns.case, columns.activity):
        required_invalid[name] = int(frame[name].map(lambda x: not isinstance(x, str) or not x.strip()).sum())
    stamps, naive, offsets = parsed_timestamps(frame[columns.timestamp])
    required_invalid[columns.timestamp] = int(stamps.isna().sum())
    report["invalid_required_values"] = required_invalid
    report["timestamps"] = {"invalid_or_naive": int(stamps.isna().sum()), "naive": naive,
                             "loaded_offsets": offsets, "normalized_timezone": "UTC"}
    if any(required_invalid.values()):
        report["confirmed_defects"].append("Invalid required field values; preprocessing will stop")
    expected_strings = [name for name in frame if name != columns.timestamp and name != "case:Amount"]
    type_invalid = {name: int(frame[name].dropna().map(lambda x: not isinstance(x, str)).sum())
                    for name in expected_strings}
    if "case:Amount" in frame:
        amount = pd.to_numeric(frame["case:Amount"], errors="coerce")
        wrong_type = frame["case:Amount"].map(lambda value: not isinstance(value, Real) or isinstance(value, bool))
        type_invalid["case:Amount"] = int((frame["case:Amount"].notna() & (wrong_type | amount.isna() | ~np.isfinite(amount))).sum())
    report["invalid_attribute_types"] = type_invalid
    report["type_expectations"] = "Domestic Declarations: string attributes, finite numeric Amount, timezone-aware timestamps. No coercion of labels or amounts."
    if any(type_invalid.values()):
        report["confirmed_defects"].append("Attributes violate the documented dataset type expectations")
    duplicate_rows = frame.duplicated(keep=False)
    report["exact_duplicates"] = {"definition": "All original flattened columns equal; no provenance columns included",
                                  "rows_in_groups": int(duplicate_rows.sum()),
                                  "excess_rows": int(frame.duplicated().sum())}
    if columns.event_id in frame:
        ids = frame[columns.event_id].dropna()
        duplicated = ids.duplicated(keep=False)
        report["duplicate_event_ids"] = {"rows_in_groups": int(duplicated.sum()),
                                          "distinct_duplicated_ids": int(ids[duplicated].nunique()),
                                          "excess_rows": int(ids.duplicated().sum()),
                                          "examples": ids[duplicated].unique().tolist()[:10]}
    conflicts = case_attribute_conflicts(frame, columns)
    report["case_attribute_consistency"] = conflicts
    if any(item["conflicting_cases"] for item in conflicts.values()):
        report["confirmed_defects"].append("Inconsistent case attributes; preprocessing will stop")
    ordered = pd.DataFrame({"case": frame[columns.case], "stamp": stamps})
    differences = ordered.groupby("case", sort=False)["stamp"].diff()
    report["chronology"] = {"backward_steps_in_source_order": int(differences.lt(pd.Timedelta(0)).sum()),
                            "cases_with_backward_steps": int(ordered.loc[differences.lt(pd.Timedelta(0)), "case"].nunique()),
                            "case_timestamp_tie_rows": int(ordered.duplicated(["case", "stamp"], keep=False).sum()),
                            "cases_with_timestamp_ties": int(ordered.loc[ordered.duplicated(["case", "stamp"], keep=False), "case"].nunique()),
                            "tie_policy": "Keep original XES event order for equal timestamps; true causal order is unknown."}
    sizes = frame.groupby(columns.case).size()
    q1, q3 = sizes.quantile([.25, .75])
    lower, upper = float(q1 - 1.5 * (q3 - q1)), float(q3 + 1.5 * (q3 - q1))
    report["trace_lengths"] = {"distribution": descriptive_stats(sizes),
                                "single_event_cases": int(sizes.eq(1).sum()),
                                "iqr_fences": [lower, upper],
                                "below_lower_fence": int(sizes.lt(lower).sum()),
                                "above_upper_fence": int(sizes.gt(upper).sum()),
                                "note": "IQR fences are descriptive flags, not exclusion rules."}
    repeated = frame.groupby([columns.case, columns.activity]).size()
    report["repetition"] = {"cases_with_repeated_activities": int(repeated[repeated.gt(1)].index.get_level_values(0).nunique()),
                             "excess_occurrences": int((repeated - 1).clip(lower=0).sum())}
    report["activity_frequency"] = frame[columns.activity].value_counts().to_dict()
    if columns.resource in frame:
        report["resource_frequency"] = frame[columns.resource].value_counts(dropna=False).to_dict()
    report["duplicate_interpretation"] = "Duplicates are retained and reported separately; repeated IDs or identical records require provenance review before any deletion."
    return report


def preprocess_events(frame, columns=Columns()):
    """Return a copy sorted by case, UTC timestamp and original source row."""
    if "_source_order" in frame:
        raise ValueError("Reserved provenance column _source_order already exists")
    quality = quality_report(frame, columns)
    if quality["confirmed_defects"]:
        raise ValueError("; ".join(quality["confirmed_defects"]))
    result = frame.copy(deep=True)
    result["_source_order"] = np.arange(len(result), dtype=np.int64)
    result[columns.timestamp] = parsed_timestamps(result[columns.timestamp])[0]
    result = result.sort_values([columns.case, columns.timestamp, "_source_order"], kind="stable").reset_index(drop=True)
    report = {"column_mapping": asdict(columns), "input_events": len(frame), "output_events": len(result),
              "input_cases": int(frame[columns.case].nunique()), "output_cases": int(result[columns.case].nunique()),
              "records_removed": 0, "attributes_preserved": list(frame.columns),
              "rows_in_different_global_positions": int((result["_source_order"].to_numpy() != np.arange(len(frame))).sum()),
              "cleaning": "No deletion, deduplication, imputation, label trimming or amount conversion applied.",
              "transformations": ["Validate explicit required mapping and dataset attribute types.",
                                  "Normalize aware timestamps to UTC; reject naive/invalid timestamps.",
                                  "Add _source_order as zero-based original flattened XES row number.",
                                  "Sort cases lexicographically, then timestamps ascending, then original source order.",
                                  "Preserve every original event and trace attribute; save Parquet without DataFrame index."],
              "limitations": ["Timestamp ties retain source order without asserting causal precedence.",
                              "No start times, processing durations, resource capacities or SLA thresholds inferred."]}
    return result, report


