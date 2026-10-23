"""Reproducible Day 2 pipeline with source fingerprints and output verification."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pandas as pd
from smartbpm.dataset import load_event_log
from smartbpm.exploration import describe_process, save_charts
from smartbpm.preprocessing import Columns, inspect_xes_source, preprocess_events, quality_report


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write_json(path, value):
    def encode(item):
        if hasattr(item, "item"):
            return item.item()
        raise TypeError(f"Cannot serialize {type(item)}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=encode), encoding="utf-8")


def run_day2(source, processed_dir, report_dir, columns=Columns(), *, export_figures=True):
    source, processed_dir, report_dir = map(Path, (source, processed_dir, report_dir))
    for directory in (processed_dir, report_dir):
        if directory.resolve() == source.parent.resolve() or source.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Output directories must be separate from the raw source directory")
    before = sha256(source)
    processed_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    xml_audit = inspect_xes_source(source)
    log, frame = load_event_log(source, validate=False)
    quality = quality_report(frame, columns)
    quality["source_sha256"] = before
    quality["xes_source_audit"] = xml_audit
    quality["trace_count"] = len(log)
    quality["empty_trace_count"] = sum(len(trace) == 0 for trace in log)
    names = [trace.attributes.get("concept:name") for trace in log]
    quality["duplicate_trace_case_names"] = len(names) - len(set(names))
    if quality["empty_trace_count"] or quality["duplicate_trace_case_names"]:
        quality["confirmed_defects"].append("Empty traces or duplicate trace case names require explicit review")
    if xml_audit["naive_timestamps"] or xml_audit["invalid_timestamps"]:
        quality["confirmed_defects"].append("Ambiguous or invalid original XES timestamps require review")
    write_json(report_dir / "data_quality_report.json", quality)
    if quality["confirmed_defects"]:
        raise ValueError("Quality report saved; resolve confirmed defects before preprocessing")
    events, preprocessing = preprocess_events(frame, columns)
    parquet = processed_dir / "domestic_declarations_cleaned.parquet"
    events.to_parquet(parquet, engine="pyarrow", index=False)
    restored = pd.read_parquet(parquet)
    pd.testing.assert_frame_equal(events, restored)
    preprocessing.update({"source_sha256": before, "output_sha256": sha256(parquet),
                          "output_file": str(parquet.resolve()), "parquet_roundtrip_verified": True,
                          "cleaning_required": False,
                          "ordering_note": "Chronological analytical ordering is a representation change; original order remains recoverable from _source_order."})
    summary, tables = describe_process(events, columns)
    summary["source_sha256"] = before
    summary["column_mapping"] = asdict(columns)
    summary["tables"] = []
    for name, table in tables.items():
        filename = f"{name}.csv"
        table.to_csv(report_dir / filename, index=False)
        summary["tables"].append(filename)
    summary["charts"] = []
    if export_figures:
        figure_dir = report_dir / "figures"
        figure_dir.mkdir(exist_ok=True)
        summary["charts"] = ["figures/" + name for name in save_charts(tables, figure_dir)]
    if sha256(source) != before:
        raise RuntimeError("Original source checksum changed during execution")
    preprocessing["source_unchanged_verified"] = True
    write_json(report_dir / "preprocessing_report.json", preprocessing)
    write_json(report_dir / "initial_eda_summary.json", summary)
    return quality, preprocessing, summary

