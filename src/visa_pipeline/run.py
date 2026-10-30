"""Main pipeline orchestration."""

import json
import logging
from pathlib import Path
from typing import Any, Callable

from .api import WikiClient
from .discover import get_pages
from .validate import (
    load_schema,
    validate_passport_file,
    load_previous_passport,
    check_safety,
    get_changes_for_changelog
)
from .publish import (
    format_passport_data,
    write_passport_file,
    write_index_json,
    write_all_json,
    write_changelog,
    write_report,
    write_summary_json
)


logger = logging.getLogger(__name__)


def load_all_existing_passports(data_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """
    Load all existing passport files.

    Returns:
        Tuple of (passport_metadata, all_passports_data)
    """
    passport_metadata = {}
    all_passports_data = {}

    passports_dir = data_dir / "passports"
    if not passports_dir.exists():
        return passport_metadata, all_passports_data

    for passport_file in passports_dir.glob("*.json"):
        iso2 = passport_file.stem
        try:
            with open(passport_file) as f:
                data = json.load(f)

            passport_metadata[iso2] = {
                "title": data["source_title"],
                "revid": int(data["source_revision"]),
                "timestamp": data["source_timestamp"],
                "record_count": len(data["records"]),
                "last_changed": data.get("generated_at", data["source_timestamp"])
            }
            all_passports_data[iso2] = data["records"]
        except Exception:
            # Skip malformed files
            pass

    return passport_metadata, all_passports_data


def load_revisions_state(state_dir: Path) -> dict[str, dict[str, Any]]:
    """Load revisions state file."""
    revisions_file = state_dir / "revisions.json"
    if not revisions_file.exists():
        return {}

    with open(revisions_file) as f:
        return json.load(f)


def save_revisions_state(state_dir: Path, revisions: dict[str, dict[str, Any]]) -> None:
    """Save revisions state file."""
    state_dir.mkdir(parents=True, exist_ok=True)
    revisions_file = state_dir / "revisions.json"

    with open(revisions_file, "w") as f:
        json.dump(revisions, f, indent=2, ensure_ascii=False)
        f.write("\n")


def needs_update(
    iso2: str,
    revid: int,
    stored_revisions: dict[str, dict[str, Any]],
    data_dir: Path,
    force: bool
) -> bool:
    """Check if a passport needs updating."""
    if force:
        return True

    # Check if output file is missing
    output_file = data_dir / "passports" / f"{iso2}.json"
    if not output_file.exists():
        return True

    # Check if revid changed
    if iso2 not in stored_revisions:
        return True

    return stored_revisions[iso2]["revid"] != revid


def run(
    data_dir: Path = Path("data"),
    state_dir: Path = Path("state"),
    out_dir: Path = Path("out"),
    only: list[str] | None = None,
    max_status_changes: int = 15,
    max_record_drop_pct: int = 10,
    force: bool = False,
    refresh_pages: bool = False,
    min_interval: float = 1.0,
    parse_page: Callable | None = None,
    client: WikiClient | None = None
) -> int:
    """
    Run the visa requirements pipeline.

    Args:
        data_dir: Data directory (published output)
        state_dir: State directory (pages, revisions)
        out_dir: Output directory (report, changelog, summary)
        only: Optional list of ISO2 codes to process
        max_status_changes: Maximum allowed status changes
        max_record_drop_pct: Maximum allowed record drop percentage
        force: Force reparse all pages
        refresh_pages: Force refresh page discovery
        min_interval: Minimum seconds between API requests
        parse_page: Parser function (for testing, defaults to real parser)
        client: WikiClient instance (for testing, defaults to real client)

    Returns:
        Exit code (0=success, 1=failure)
    """
    # Import parser lazily
    if parse_page is None:
        try:
            from .extract_main import parse_page as real_parse_page
            parse_page = real_parse_page
        except ImportError:
            logger.error("Parser modules not available (expected on pipeline branch)")
            return 1

    # Initialize client
    if client is None:
        client = WikiClient(min_interval=min_interval)

    # Discover pages
    logger.info("Discovering pages...")
    overrides_path = Path(__file__).parent / "overrides" / "passports.json"
    pages = get_pages(client, state_dir, overrides_path, refresh=refresh_pages)

    # Filter to mapped pages
    mapped_pages = [p for p in pages if p["passport"] is not None]
    unmapped_pages = [p for p in pages if p["passport"] is None]

    logger.info(f"Found {len(pages)} pages, {len(mapped_pages)} mapped")

    # Filter by --only
    if only:
        only_set = set(only)
        mapped_pages = [p for p in mapped_pages if p["passport"] in only_set]
        logger.info(f"Filtered to {len(mapped_pages)} pages (--only)")

    # Load stored revisions
    stored_revisions = load_revisions_state(state_dir)

    # Get revision info for all pages and template
    logger.info("Fetching revision info...")
    titles = [p["title"] for p in mapped_pages]

    # Add template title
    TEMPLATE_TITLE = "Template:Transcluded sections for the visa articles"
    try:
        from .transclusions import TEMPLATE_TITLE as imported_title
        TEMPLATE_TITLE = imported_title
    except ImportError:
        pass

    titles.append(TEMPLATE_TITLE)

    revision_info = client.revisions(titles)

    # Check if template changed and if any pages need parsing
    template_revid = None
    if TEMPLATE_TITLE in revision_info:
        template_revid = revision_info[TEMPLATE_TITLE]["revid"]
        stored_template_revid = stored_revisions.get("_template", {}).get("revid")

        if stored_template_revid is not None and template_revid != stored_template_revid:
            logger.info("Template changed - will reparse all pages")
            force = True

    # Determine if any pages will be parsed
    any_pages_to_parse = False
    for page_info in mapped_pages:
        title = page_info["title"]
        if title in revision_info:
            revid = revision_info[title]["revid"]
            if needs_update(page_info["passport"], revid, stored_revisions, data_dir, force):
                any_pages_to_parse = True
                break

    # Fetch template if any pages will be parsed
    template_wikitext = None
    transclusions = {}
    if any_pages_to_parse and TEMPLATE_TITLE in revision_info:
        logger.info("Fetching template...")
        template_wikitext, _ = client.page_wikitext(TEMPLATE_TITLE)

        # Update stored revisions
        stored_revisions["_template"] = {
            "revid": template_revid,
            "timestamp": revision_info[TEMPLATE_TITLE]["timestamp"]
        }

        # Parse template
        try:
            from .transclusions import parse_template as do_parse_template
            transclusions = do_parse_template(template_wikitext)
        except ImportError:
            pass

    # Load all existing passport files first (so --only and failures don't lose data)
    passport_metadata, all_passports_data = load_all_existing_passports(data_dir)

    # Process each passport
    results = {
        "pages_found": len(pages),
        "pages_mapped": len(mapped_pages),
        "pages_unmapped": unmapped_pages,
        "pages_parsed": 0,
        "pages_skipped_unchanged": 0,
        "rows": 0,
        "blocked": [],
        "failed": [],
        "unmapped_statuses": [],
        "unmapped_destinations": [],
        "changes": 0
    }

    all_changes = []
    blocked_passports = {}
    exit_code = 0

    # Load schema
    schema_path = Path(__file__).parent / "schema" / "passport.schema.json"
    schema = load_schema(schema_path)

    for page_info in mapped_pages:
        iso2 = page_info["passport"]
        title = page_info["title"]

        # Check if we have revision info
        if title not in revision_info:
            logger.warning(f"{iso2}: No revision info, skipping")
            results["failed"].append({
                "passport": iso2,
                "reason": "no revision info"
            })
            exit_code = 1
            continue

        revid = revision_info[title]["revid"]
        timestamp = revision_info[title]["timestamp"]

        # Check if update needed
        if not needs_update(iso2, revid, stored_revisions, data_dir, force):
            logger.info(f"{iso2}: Unchanged, skipping")
            results["pages_skipped_unchanged"] += 1
            # Data already loaded, just ensure metadata is current
            # (it was loaded from the file, which has correct info)
            continue

        logger.info(f"{iso2}: Parsing {title}...")

        try:
            # Fetch page
            wikitext, page_revid = client.page_wikitext(title)

            # Parse page
            parse_result = parse_page(
                wikitext,
                passport=iso2,
                title=title,
                revid=page_revid,
                transclusions=transclusions
            )

            # Collect unmapped items
            results["unmapped_statuses"].extend(parse_result.unmapped_statuses)
            results["unmapped_destinations"].extend(parse_result.unmapped_destinations)

            # Format passport data
            passport_data = format_passport_data(
                passport=iso2,
                title=title,
                revid=page_revid,
                timestamp=timestamp,
                records=parse_result.records
            )

            # Validate
            validate_passport_file(passport_data, schema)

            # Load previous data
            previous_data = load_previous_passport(data_dir, iso2)

            # Check for zero records on first run
            if len(parse_result.records) == 0 and previous_data is None:
                logger.warning(f"{iso2}: FAILED - no rows parsed (new page)")
                results["failed"].append({
                    "passport": iso2,
                    "reason": "no rows parsed (new page)"
                })
                # Don't write file, don't change exit code, keep going
                continue

            # Check safety
            is_safe, reason = check_safety(
                passport_data,
                previous_data,
                max_status_changes,
                max_record_drop_pct
            )

            if not is_safe:
                # Zero records where previous had records is FAILED (exit 1), not blocked
                if reason and reason.startswith("zero records"):
                    logger.error(f"{iso2}: FAILED - {reason}")
                    results["failed"].append({
                        "passport": iso2,
                        "reason": reason
                    })
                    exit_code = 1
                    # Keep old file unchanged (already loaded in index/all)
                    continue

                # Other safety violations are blocked (exit 0)
                logger.warning(f"{iso2}: BLOCKED - {reason}")
                results["blocked"].append({
                    "passport": iso2,
                    "reason": reason
                })
                blocked_passports[iso2] = {
                    "title": title,
                    "revid": revid,
                    "timestamp": timestamp,
                    "record_count": len(parse_result.records)
                }

                # Keep previous data in index and all.json (already loaded)

                continue

            # Get changes for changelog
            changes = get_changes_for_changelog(passport_data, previous_data)
            all_changes.extend(changes)
            results["changes"] += len(changes)

            # Write passport file
            changed = write_passport_file(data_dir, passport_data, previous_data)

            # Update metadata
            passport_metadata[iso2] = {
                "title": title,
                "revid": page_revid,
                "timestamp": timestamp,
                "record_count": len(parse_result.records),
                "last_changed": passport_data["generated_at"] if changed else (
                    previous_data.get("generated_at", timestamp) if previous_data else passport_data["generated_at"]
                )
            }

            all_passports_data[iso2] = parse_result.records
            results["pages_parsed"] += 1

            # Update stored revisions
            stored_revisions[iso2] = {
                "revid": page_revid,
                "timestamp": timestamp
            }

            logger.info(f"{iso2}: Completed - {len(parse_result.records)} records")

        except Exception as e:
            logger.error(f"{iso2}: FAILED - {e}", exc_info=True)
            results["failed"].append({
                "passport": iso2,
                "reason": str(e)
            })
            exit_code = 1

    # Check for passports whose pages vanished from category
    mapped_iso2s = {p["passport"] for p in mapped_pages}
    for iso2 in list(passport_metadata.keys()):
        if iso2 not in mapped_iso2s:
            # Page vanished but we have data - keep it with a warning
            logger.warning(f"{iso2}: Page vanished from category, keeping existing data")

    # Calculate total rows from all passport data
    results["rows"] = sum(len(records) for records in all_passports_data.values())

    # Save revisions state
    save_revisions_state(state_dir, stored_revisions)

    # Write output files
    logger.info("Writing output files...")
    write_index_json(data_dir, passport_metadata, blocked_passports)
    write_all_json(data_dir, all_passports_data)
    write_changelog(out_dir, all_changes)
    write_report(out_dir, results)
    write_summary_json(out_dir, results)

    logger.info(f"Pipeline complete - {results['pages_parsed']} parsed, {results['rows']} rows")

    return exit_code
