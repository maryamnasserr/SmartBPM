"""Dashboard cohort semantics, analytical preparation and real Streamlit execution."""
from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from smartbpm.dashboard import C, filter_cases, load_dashboard_events, prepare_dashboard
from smartbpm.dashboard_charts import dashboard_charts

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def events():
    return pd.DataFrame({C.case: ["a", "a", "b", "b", "c"],
                         C.activity: ["Submit", "End", "Submit", "Reject", "Save"],
                         C.resource: ["R1", "R2", "R2", "R2", "R1"],
                         C.timestamp: pd.to_datetime(["2020-01-01", "2020-01-03", "2020-01-02", "2020-01-02", "2020-01-04"], utc=True),
                         "_source_order": range(5)})


def test_full_cohort_counts_and_charts(events):
    summary, tables = prepare_dashboard(events)
    assert (summary["total_cases"], summary["total_events"], summary["total_activities"]) == (3, 5, 4)
    assert summary["duration_days"]["mean"] == pytest.approx(2 / 3)
    selected = filter_cases(events, tables["case_summary"])
    pd.testing.assert_frame_equal(selected, events)
    charts = dashboard_charts(tables)
    assert len(charts) == 8
    assert list(charts["trace_length"].data[0].y) == [1, 2]
    assert sum(charts["activity_frequency"].data[0].x) == 5
    assert list(charts["duration"].data[0].x) == [2, 0, 0]
    for fig in charts.values():
        assert fig.to_json()


def test_activity_and_resource_keep_whole_cases(events):
    _, tables = prepare_dashboard(events)
    selected = filter_cases(events, tables["case_summary"], activities=["End"], resources=["R1"])
    assert selected[C.case].tolist() == ["a", "a"]
    summary, _ = prepare_dashboard(selected)
    assert summary["duration_days"]["50%"] == 2
    assert summary["total_activities"] == 2


@pytest.mark.parametrize("options", [{"activities": []}, {"resources": []}, {"activities": ["Absent"]}])
def test_empty_selections_are_safe(events, options):
    _, tables = prepare_dashboard(events)
    selected = filter_cases(events, tables["case_summary"], **options)
    summary, prepared = prepare_dashboard(selected)
    assert selected.empty
    assert summary["total_cases"] == summary["total_events"] == 0
    assert summary["duration_days"]["50%"] is None
    assert dashboard_charts(prepared) == {}


def test_date_and_duration_bounds(events):
    _, tables = prepare_dashboard(events)
    cases = tables["case_summary"]
    selected = filter_cases(events, cases, start_date=date(2020, 1, 2), end_date=date(2020, 1, 2))
    assert selected[C.case].tolist() == ["b", "b"]
    assert filter_cases(events, cases, duration_range=(2, 2))[C.case].tolist() == ["a", "a"]
    assert filter_cases(events, cases, duration_range=(0, 0))[C.case].nunique() == 2
    with pytest.raises(ValueError):
        filter_cases(events, cases, start_date=date(2021, 1, 1), end_date=date(2020, 1, 1))
    with pytest.raises(ValueError):
        filter_cases(events, cases, duration_range=(2, 1))


def test_filters_do_not_mutate_input(events):
    before = events.copy(deep=True)
    _, tables = prepare_dashboard(events)
    filter_cases(events, tables["case_summary"], activities=["Save"])
    pd.testing.assert_frame_equal(events, before)


def test_parquet_loading_and_missing_schema(events, tmp_path):
    path = tmp_path / "events.parquet"
    events.to_parquet(path, index=False)
    pd.testing.assert_frame_equal(load_dashboard_events(path), events)
    events.drop(columns=C.resource).to_parquet(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_dashboard_events(path)
    with pytest.raises(FileNotFoundError):
        load_dashboard_events(tmp_path / "absent.parquet")


def test_reject_duplicate_provenance(events, tmp_path):
    events.loc[1, "_source_order"] = 0
    path = tmp_path / "bad.parquet"
    events.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="provenance"):
        load_dashboard_events(path)


@pytest.mark.integration
def test_streamlit_real_totals_filters_and_navigation():
    from streamlit.testing.v1 import AppTest
    if not (ROOT / "data/processed/domestic_declarations_cleaned.parquet").exists():
        pytest.skip("Processed local dataset unavailable")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not app.exception
    assert [m.value for m in app.metric[:3]] == ["10,500", "56,437", "17"]
    assert len(app.get("plotly_chart")) == 2
    for page in ("Activities & resources", "Variants & repetition", "Case boundaries", "Case explorer"):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
    app.sidebar.radio[0].set_value("Overview").run()
    app.sidebar.multiselect[0].set_value(["Declaration FOR_APPROVAL by ADMINISTRATION"]).run()
    assert not app.exception
    assert app.metric[0].value == "1"
    assert int(app.metric[1].value.replace(",", "")) > 1
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert app.metric[0].value == "0"
    assert not app.get("plotly_chart")
    assert any("No cases match" in element.value for element in app.info)
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "10,500"
    app.sidebar.multiselect[1].set_value([]).run()
    assert not app.exception
    assert app.metric[0].value == "0"
    app.sidebar.button[0].click().run()
    app.sidebar.multiselect[1].set_value(["SYSTEM"]).run()
    assert not app.exception
    assert 0 < int(app.metric[0].value.replace(",", "")) < 10500
    app.sidebar.button[0].click().run()
    app.sidebar.date_input[0].set_value((date(2017, 1, 9), date(2017, 1, 9))).run()
    assert not app.exception
    raw = pd.read_parquet(ROOT / "data/processed/domestic_declarations_cleaned.parquet")
    starts = raw.groupby(C.case)[C.timestamp].min()
    assert int(app.metric[0].value.replace(",", "")) == int(starts.dt.date.eq(date(2017, 1, 9)).sum())
    app.sidebar.button[0].click().run()
    app.sidebar.slider[0].set_value((1., 20.)).run()
    assert not app.exception
    assert 0 < int(app.metric[0].value.replace(",", "")) < 10500


@pytest.mark.integration
def test_existing_dataset_fingerprints_preserved():
    import hashlib
    import json
    raw = ROOT / "data/raw/DomesticDeclarations.xes"
    processed = ROOT / "data/processed/domestic_declarations_cleaned.parquet"
    if not raw.exists() or not processed.exists():
        pytest.skip("Local datasets unavailable")
    manifest = json.loads((ROOT / "outputs/reports/preprocessing_report.json").read_text())
    for path, key in ((raw, "source_sha256"), (processed, "output_sha256")):
        with path.open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == manifest[key]

