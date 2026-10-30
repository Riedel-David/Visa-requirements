"""CLI entry point."""

import sys
import logging
import argparse
from pathlib import Path

from .run import run


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Wikipedia visa requirements data pipeline"
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["run"],
        default="run",
        help="Command to execute (default: run)"
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data"),
        help="Data directory (published output, default: data)"
    )

    parser.add_argument(
        "--state",
        type=Path,
        default=Path("state"),
        help="State directory (pages, revisions, default: state)"
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out"),
        help="Output directory (report, changelog, summary, default: out)"
    )

    parser.add_argument(
        "--only",
        type=str,
        help="Only process these ISO2 codes (comma-separated, e.g., DE,US,FR)"
    )

    parser.add_argument(
        "--max-status-changes",
        type=int,
        default=15,
        help="Maximum allowed status changes before blocking (default: 15)"
    )

    parser.add_argument(
        "--max-record-drop-pct",
        type=int,
        default=10,
        help="Maximum allowed record drop percentage before blocking (default: 10)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Reparse all pages and bypass the safety thresholds (does not bypass the 24h revision cooling-off)"
    )

    parser.add_argument(
        "--refresh-pages",
        action="store_true",
        help="Force refresh page discovery"
    )

    parser.add_argument(
        "--min-interval",
        type=float,
        default=1.0,
        help="Minimum seconds between API requests (default: 1.0)"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr
    )

    # Parse --only
    only_codes = None
    if args.only:
        only_codes = [code.strip().upper() for code in args.only.split(",")]

    # Run pipeline
    exit_code = run(
        data_dir=args.data,
        state_dir=args.state,
        out_dir=args.out,
        only=only_codes,
        max_status_changes=args.max_status_changes,
        max_record_drop_pct=args.max_record_drop_pct,
        force=args.force,
        refresh_pages=args.refresh_pages,
        min_interval=args.min_interval
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
