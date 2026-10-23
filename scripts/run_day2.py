"""Quality audit, non-destructive preprocessing and observed process exploration."""
import argparse
import logging
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smartbpm.day2 import run_day2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/raw/DomesticDeclarations.xes")
    parser.add_argument("--processed-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "outputs/reports")
    parser.add_argument("--no-figures", action="store_true", help="Skip optional static PNG exports")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        quality, preprocessing, summary = run_day2(args.dataset, args.processed_dir, args.report_dir, export_figures=not args.no_figures)
    except (OSError, ValueError, TypeError, RuntimeError, AssertionError, ET.ParseError) as exc:
        logging.error("Day 2 failed: %s", exc)
        return 1
    logging.info("Verified %d events, %d cases, %d activities, %d variants", summary["total_events"], summary["total_cases"], summary["total_activities"], summary["variant_count"])
    logging.info("No records removed. Parquet round trip and original source checksum verified.")
    logging.info("Reports: %s", args.report_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


