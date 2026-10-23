"""Run from any directory with the project's Python interpreter."""
import argparse
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smartbpm.dataset import profile_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/raw/DomesticDeclarations.xes")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reports/dataset_profile.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.output.resolve() == args.dataset.resolve():
            raise ValueError("Report output must differ from the source dataset")
        report = profile_dataset(args.dataset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        logging.error("Inspection failed: %s", exc)
        return 1
    logging.info("Events: %s; cases: %s; activities: %s", report["event_count"], report["case_count"], report["activity_count"])
    print(json.dumps(report, indent=2, ensure_ascii=False))
    logging.info("Saved report to %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
