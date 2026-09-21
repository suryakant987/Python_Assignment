from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from asset_registry.config import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

from asset_registry.db.session import get_session_factory, init_db
from asset_registry.ingest.outputs import write_geojson, write_rejects, write_summary_report
from asset_registry.ingest.pipeline import MissingColumnsError, StrictIngestAborted, ingest_csv_file
from asset_registry.logging_setup import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest-survey",
        description=(
            "Load a day's handheld GPS export, clean the rows, store accepted "
            "assets, and write a rejects file, a map file and a summary report."
        ),
    )
    parser.add_argument(
        "csv_path",
        help="Path to the CSV file exported by the handheld unit.",
    )
    parser.add_argument(
        "--rejects",
        default="outputs/rejects.csv",
        help="Where to write rejected rows (default: outputs/rejects.csv).",
    )
    parser.add_argument(
        "--map",
        default="outputs/assets.geojson",
        dest="map_path",
        help="Where to write the GeoJSON map file (default: outputs/assets.geojson).",
    )
    parser.add_argument(
        "--report",
        default="outputs/summary.txt",
        help="Where to write the plain-text summary (default: outputs/summary.txt).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Abort the whole run if any row is rejected. Use this for already-cleaned data.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logging()
    ingest_log = __import__("logging").getLogger("asset_registry.ingest")

    csv_path = Path(args.csv_path)
    init_db()
    session = get_session_factory()()
    try:
        result = ingest_csv_file(session, csv_path, strict=args.strict)
    except FileNotFoundError as exc:
        parser.exit(2, f"error: {exc}\n")
    except MissingColumnsError as exc:
        parser.exit(2, f"error: {exc}\n")
    except StrictIngestAborted as exc:
        session.rollback()
        ingest_log.info(
            "run aborted strict=1 source=%s reason=%s",
            csv_path,
            exc.reason,
        )
        print("STRICT MODE: run aborted. No records were stored.")
        print(f"Reason: {exc.reason}")
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rejects_path = Path(args.rejects)
    map_path = Path(args.map_path)
    report_path = Path(args.report)
    write_rejects(rejects_path, result.rejects)
    write_geojson(map_path, result.accepted)
    write_summary_report(report_path, result)

    ingest_log.info(
        "run source=%s read=%s accepted=%s rejected=%s rejects_file=%s",
        csv_path,
        result.rows_read,
        result.rows_accepted,
        result.rows_rejected,
        rejects_path,
    )
    logger.info("ingestion complete")

    print("Ingestion complete.")
    print(f"  Rows read:      {result.rows_read}")
    print(f"  Rows accepted:  {result.rows_accepted}")
    print(f"  Rows rejected:  {result.rows_rejected}")
    print(f"  Rejects file:   {rejects_path}")
    print(f"  Map file:       {map_path}")
    print(f"  Summary report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
