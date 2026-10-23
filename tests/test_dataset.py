from pathlib import Path
import sys
import pandas as pd
import pytest
from smartbpm.dataset import load_event_log, validate_events, profile_dataset

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def xes(tmp_path):
    path = tmp_path / "sample.xes"
    path.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0" xmlns="http://www.xes-standard.org/">
<trace><string key="concept:name" value="case-1"/>
<event><string key="concept:name" value="Submit"/>
<date key="time:timestamp" value="2020-01-01T10:00:00+00:00"/></event>
</trace></log>''', encoding="utf-8")
    return path


def test_environment_and_structure():
    assert sys.version_info[:2] == (3, 12)
    assert sys.prefix != sys.base_prefix
    for name in ("data/raw", "data/processed", "outputs/reports", "outputs/models", "outputs/simulations", "src/smartbpm", "scripts", "tests", "docs"):
        assert (ROOT / name).is_dir()


def test_load_and_profile(xes):
    before = xes.read_bytes()
    log, frame = load_event_log(xes)
    assert len(log) == len(frame) == 1
    report = profile_dataset(xes)
    assert report["case_count"] == report["activity_count"] == 1
    assert report["activities"] == {"Submit": 1}
    assert report["missing_values"]["time:timestamp"] == 0
    assert xes.read_bytes() == before


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_event_log(tmp_path / "absent.xes")


@pytest.mark.parametrize("content", ["", "not XML", "<log><trace>"])
def test_invalid_file(tmp_path, content):
    path = tmp_path / "bad.xes"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_event_log(path)


@pytest.mark.parametrize("problem", ["empty", "missing_column", "null", "invalid_date", "blank"])
def test_required_validation(problem):
    frame = pd.DataFrame({"case:concept:name": ["one"], "concept:name": ["Submit"], "time:timestamp": ["2020-01-01T00:00:00Z"]})
    if problem == "empty":
        frame = frame.iloc[:0]
    elif problem == "missing_column":
        frame = frame.drop(columns="concept:name")
    elif problem == "null":
        frame.loc[0, "concept:name"] = None
    elif problem == "blank":
        frame.loc[0, "case:concept:name"] = " "
    else:
        frame.loc[0, "time:timestamp"] = "invalid"
    with pytest.raises(ValueError):
        validate_events(frame)


@pytest.mark.integration
def test_real_dataset():
    path = ROOT / "data/raw/DomesticDeclarations.xes"
    if not path.exists():
        pytest.skip("Local dataset unavailable")
    report = profile_dataset(path)
    assert report["event_count"] > 0
    assert report["trace_count"] == report["case_count"]
    assert all(report["missing_values"][key] == 0 for key in ("case:concept:name", "concept:name", "time:timestamp"))


def test_inspection_cli_missing_dataset(tmp_path):
    import subprocess
    result = subprocess.run([sys.executable, str(ROOT / "scripts/inspect_dataset.py"), "--dataset", str(tmp_path / "absent.xes"), "--output", str(tmp_path / "report.json")], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Inspection failed" in result.stderr
    assert not (tmp_path / "report.json").exists()


def test_inspection_cli_rejects_source_overwrite(xes):
    import subprocess
    before = xes.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/inspect_dataset.py"), "--dataset", str(xes), "--output", str(xes)], capture_output=True, text=True)
    assert result.returncode == 1
    assert xes.read_bytes() == before


def test_original_attribute_scopes_preserved(xes):
    log, frame = load_event_log(xes)
    assert "case:concept:name" in frame.columns
    assert "case:concept:name" not in log[0][0]
    report = profile_dataset(xes)
    assert "concept:name" in report["trace_attributes"]
    assert not any(key.startswith("case:") for key in report["event_attributes"])
