"""Day 2 invariants and independent small-log oracles."""
import json
from pathlib import Path
import pandas as pd
import pytest
from smartbpm.preprocessing import Columns, quality_report, preprocess_events, inspect_xes_source
from smartbpm.exploration import describe_process
from smartbpm.day2 import run_day2, sha256
ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def events():
    return pd.DataFrame({
        "case:concept:name": ["b", "a", "a", "a", "a"],
        "concept:name": ["Only", "End", "Start", "Start", "Mid"],
        "time:timestamp": ["2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z", "2020-01-01T02:00:00+02:00", "2020-01-01T00:00:00Z", "2020-01-01T12:00:00Z"],
        "id": ["b1", "a4", "a1", "a2", "a3"],
        "org:resource": ["SYSTEM"] * 5,
        "case:Amount": [20., 10., 10., 10., 10.]})


def test_timezone_order_counts_and_attributes(events):
    before = events.copy(deep=True)
    cleaned, report = preprocess_events(events)
    assert str(cleaned["time:timestamp"].dt.tz) == "UTC"
    assert cleaned.id.tolist() == ["a1", "a2", "a3", "a4", "b1"]
    assert cleaned._source_order.tolist() == [2, 3, 4, 1, 0]
    assert report["input_events"] == report["output_events"] == 5
    assert report["input_cases"] == report["output_cases"] == 2
    assert report["records_removed"] == 0
    pd.testing.assert_frame_equal(events, before)
    restored = cleaned.sort_values("_source_order").reset_index(drop=True)
    pd.testing.assert_frame_equal(restored.drop(columns=["time:timestamp", "_source_order"]), events.drop(columns="time:timestamp"))
    pd.testing.assert_frame_equal(cleaned, preprocess_events(events)[0])


@pytest.mark.parametrize("field,value", [("case:concept:name", None), ("case:concept:name", 42), ("concept:name", " "), ("time:timestamp", "bad"), ("time:timestamp", "2020-01-01"), ("time:timestamp", 123), ("case:Amount", "not money")])
def test_reject_invalid_fields(events, field, value):
    events[field] = events[field].astype(object)
    events.loc[0, field] = value
    with pytest.raises(ValueError):
        preprocess_events(events)


@pytest.mark.parametrize("field", ["case:concept:name", "concept:name", "time:timestamp"])
def test_missing_schema(events, field):
    with pytest.raises(ValueError):
        preprocess_events(events.drop(columns=field))


def test_empty_log(events):
    with pytest.raises(ValueError):
        preprocess_events(events.iloc[:0])


def test_duplicate_records_and_ids_are_separate(events):
    events.loc[1, "id"] = "b1"
    report = quality_report(events)
    assert report["exact_duplicates"]["excess_rows"] == 0
    assert report["duplicate_event_ids"]["rows_in_groups"] == 2
    frame = pd.concat([events, events.iloc[[0]]], ignore_index=True)
    report = quality_report(frame)
    assert report["exact_duplicates"]["rows_in_groups"] == 2
    assert report["exact_duplicates"]["excess_rows"] == 1
    assert report["duplicate_event_ids"]["rows_in_groups"] == 3
    assert len(preprocess_events(frame)[0]) == 6


def test_case_attribute_consistency(events):
    events.loc[2, "case:Amount"] = 999.
    report = quality_report(events)
    assert report["case_attribute_consistency"]["case:Amount"]["conflicting_cases"] == 1
    assert report["case_attribute_consistency"]["case:Amount"]["example_case_ids"] == ["a"]
    with pytest.raises(ValueError, match="Inconsistent case attributes"):
        preprocess_events(events)


def test_conflicting_missing_case_attribute(events):
    events.loc[2, "case:Amount"] = float("nan")
    assert quality_report(events)["case_attribute_consistency"]["case:Amount"]["conflicting_cases"] == 1


def test_original_order_quality_and_ties(events):
    report = quality_report(events)
    assert report["chronology"]["backward_steps_in_source_order"] == 1
    assert report["chronology"]["cases_with_backward_steps"] == 1
    assert report["chronology"]["case_timestamp_tie_rows"] == 2
    assert report["repetition"]["cases_with_repeated_activities"] == 1
    assert report["trace_lengths"]["single_event_cases"] == 1


def test_custom_column_mapping(events):
    mapped = events.rename(columns={"case:concept:name": "case_key", "concept:name": "activity", "time:timestamp": "at"})
    columns = Columns(case="case_key", activity="activity", timestamp="at")
    cleaned, _ = preprocess_events(mapped, columns)
    assert cleaned.id.tolist() == ["a1", "a2", "a3", "a4", "b1"]
    assert describe_process(cleaned, columns)[0]["total_cases"] == 2


def test_reserved_provenance_rejected(events):
    events["_source_order"] = range(len(events))
    with pytest.raises(ValueError, match="Reserved"):
        preprocess_events(events)


def test_descriptive_statistics_oracle(events):
    cleaned, _ = preprocess_events(events)
    summary, tables = describe_process(cleaned)
    cases = tables["case_summary"].set_index("case:concept:name")
    assert cases.loc["a", "elapsed_days"] == 1
    assert cases.loc["b", "elapsed_days"] == 0
    assert summary["duration_days"]["mean"] == .5
    assert summary["variant_count"] == 2
    assert summary["cases_with_repeated_activities"] == 1
    assert summary["adjacent_repeated_activity_events"] == 1
    assert summary["common_starts"] == {"Start": 1, "Only": 1}
    assert summary["common_ends"] == {"End": 1, "Only": 1}
    assert tables["process_variants"].case_count.sum() == 2
    assert tables["activity_frequency"].event_count.sum() == 5


@pytest.fixture
def small_xes(tmp_path):
    path = tmp_path / "raw" / "sample.xes"
    path.parent.mkdir()
    path.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0"><trace><string key="concept:name" value="case-1"/>
<float key="Amount" value="10.0"/>
<event><string key="id" value="e1"/><string key="concept:name" value="Submit"/><string key="org:resource" value="SYSTEM"/><date key="time:timestamp" value="2020-01-01T10:00:00+01:00"/></event>
<event><string key="id" value="e2"/><string key="concept:name" value="End"/><string key="org:resource" value="SYSTEM"/><date key="time:timestamp" value="2020-01-02T11:00:00+02:00"/></event>
</trace></log>''', encoding="utf-8")
    return path


def test_raw_timezone_audit(small_xes):
    audit = inspect_xes_source(small_xes)
    assert audit["timestamp_offsets"] == {"1:00:00": 1, "2:00:00": 1}
    assert audit["invalid_timestamps"] == audit["naive_timestamps"] == 0
    assert audit["attribute_xml_types"]["time:timestamp|date"] == 2


def test_pipeline_outputs_and_reproducibility(small_xes, tmp_path):
    before = sha256(small_xes)
    processed, reports = tmp_path / "processed", tmp_path / "reports"
    first = run_day2(small_xes, processed, reports)
    assert first[1]["source_unchanged_verified"]
    assert first[1]["parquet_roundtrip_verified"]
    assert first[2]["duration_days"]["mean"] == 1
    assert len(pd.read_parquet(processed / "domestic_declarations_cleaned.parquet")) == 2
    for name in ("data_quality_report.json", "preprocessing_report.json", "initial_eda_summary.json"):
        json.loads((reports / name).read_text(encoding="utf-8"))
    for name in first[2]["tables"]:
        assert not pd.read_csv(reports / name).columns.empty
    for name in first[2]["charts"]:
        assert (reports / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    hashes = {p.relative_to(reports).as_posix(): sha256(p) for p in reports.rglob("*") if p.is_file()}
    parquet_hash = sha256(processed / "domestic_declarations_cleaned.parquet")
    assert run_day2(small_xes, processed, reports) == first
    assert {p.relative_to(reports).as_posix(): sha256(p) for p in reports.rglob("*") if p.is_file()} == hashes
    assert sha256(processed / "domestic_declarations_cleaned.parquet") == parquet_hash
    assert sha256(small_xes) == before


def test_reject_output_in_raw(small_xes, tmp_path):
    with pytest.raises(ValueError, match="separate"):
        run_day2(small_xes, small_xes.parent, tmp_path / "reports")


@pytest.mark.integration
def test_real_day2_pipeline(tmp_path):
    source = ROOT / "data/raw/DomesticDeclarations.xes"
    if not source.exists():
        pytest.skip("Local dataset unavailable")
    quality, prep, summary = run_day2(source, tmp_path / "processed", tmp_path / "reports")
    assert summary["total_cases"] == prep["input_cases"] == prep["output_cases"]
    assert summary["total_events"] == prep["input_events"] == prep["output_events"]
    assert quality["confirmed_defects"] == []
    assert prep["records_removed"] == 0
    assert prep["source_unchanged_verified"] and prep["parquet_roundtrip_verified"]


def test_pipeline_rejects_naive_source_and_saves_quality(small_xes, tmp_path):
    small_xes.write_text(small_xes.read_text().replace("+01:00", ""), encoding="utf-8")
    reports = tmp_path / "reports"
    processed = tmp_path / "processed"
    with pytest.raises(ValueError, match="Quality report saved"):
        run_day2(small_xes, processed, reports)
    quality = json.loads((reports / "data_quality_report.json").read_text())
    assert quality["xes_source_audit"]["naive_timestamps"] == 1
    assert not (processed / "domestic_declarations_cleaned.parquet").exists()


@pytest.mark.parametrize("amount", ["10.0", True, float("inf")])
def test_amount_types_are_not_silently_coerced(events, amount):
    events["case:Amount"] = events["case:Amount"].astype(object)
    events.loc[0, "case:Amount"] = amount
    with pytest.raises(ValueError):
        preprocess_events(events)



def test_static_exports_are_optional_and_subfolder_scoped(small_xes,tmp_path):
    processed,reports=tmp_path/'processed',tmp_path/'reports'
    _,_,summary=run_day2(small_xes,processed,reports,export_figures=False)
    assert summary['charts']==[]
    assert not list(reports.rglob('*.png'))
    _,_,summary=run_day2(small_xes,processed,reports)
    assert all(name.startswith('figures/') for name in summary['charts'])
    assert len(list((reports/'figures').glob('*.png')))==7
    assert not list(reports.glob('*.png'))
