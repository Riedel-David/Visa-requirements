"""Output file publishing."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


# Disclaimer text from contracts.md
DISCLAIMER = (
    "Visa data is community-sourced from Wikipedia and may be incomplete, "
    "outdated or wrong. Always verify entry requirements with the official "
    "embassy or government source of the destination before travelling."
)


def format_passport_data(
    passport: str,
    title: str,
    revid: int,
    timestamp: str,
    records: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Format passport data for output file.

    Args:
        passport: ISO2 passport code
        title: Wikipedia page title
        revid: Revision ID
        timestamp: ISO timestamp
        records: List of visa requirement records

    Returns:
        Formatted passport data dict
    """
    # Sort records by destination, then area (null first)
    sorted_records = sorted(
        records,
        key=lambda r: (r["destination"], r["area"] is not None, r["area"] or "")
    )

    return {
        "schema_version": "1.0.0",
        "passport": passport,
        "source_title": title,
        "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        "source_revision": str(revid),
        "source_timestamp": timestamp,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "license": "CC BY-SA 4.0",
        "attribution": "Derived from Wikipedia (see LICENSE-DATA.md)",
        "records": sorted_records
    }


def _semantic_content(passport_data: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Passport code and records without provenance fields, in stable order."""
    records = [
        {k: v for k, v in r.items() if k != "source_revision"}
        for r in passport_data["records"]
    ]
    records.sort(key=lambda r: (r["destination"], r["area"] is not None, r["area"] or ""))
    return passport_data["passport"], records


def write_passport_file(
    data_dir: Path,
    passport_data: dict[str, Any],
    previous_data: dict[str, Any] | None = None
) -> bool:
    """
    Write passport JSON file, only if the visa data changed (provenance-only
    changes such as a new source_revision leave the file untouched).

    Args:
        data_dir: Data directory
        passport_data: Passport data dict
        previous_data: Previous passport data (for change detection)

    Returns:
        True if file was written (changed), False if unchanged
    """
    passport = passport_data["passport"]
    output_path = data_dir / "passports" / f"{passport}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Only the visa data counts as a change. Provenance (per-record
    # source_revision, header revision/timestamp, generated_at) is ignored, so a
    # Wikipedia edit that leaves the data alone keeps the old file untouched.
    if previous_data is not None and (
        _semantic_content(passport_data) == _semantic_content(previous_data)
    ):
        return False

    # Write file
    with open(output_path, "w") as f:
        json.dump(passport_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return True


def write_index_json(
    data_dir: Path,
    passports: dict[str, dict[str, Any]],
    blocked_passports: dict[str, dict[str, Any]]
) -> None:
    """
    Write data/index.json with metadata for all passports.

    Args:
        data_dir: Data directory
        passports: Dict of ISO2 -> passport metadata
        blocked_passports: Dict of ISO2 -> {title, revid, timestamp, record_count} for blocked passports
    """
    # Load existing index to get previous entries for blocked passports
    index_path = data_dir / "index.json"
    existing_index = {}
    if index_path.exists():
        with open(index_path) as f:
            old_data = json.load(f)
            existing_index = old_data.get("passports", {})

    # Build passport entries
    passport_entries = {}

    for iso2, meta in passports.items():
        passport_entries[iso2] = {
            "file": f"passports/{iso2}.json",
            "source_title": meta["title"],
            "source_url": f"https://en.wikipedia.org/wiki/{meta['title'].replace(' ', '_')}",
            "source_revision": str(meta["revid"]),
            "source_timestamp": meta["timestamp"],
            "record_count": meta["record_count"],
            "last_changed": meta["last_changed"]
        }

    # For blocked passports, carry over previous entry
    for iso2, meta in blocked_passports.items():
        if iso2 in existing_index:
            passport_entries[iso2] = existing_index[iso2]

    # Stable key order: processing order varies between runs and would rewrite the whole file
    passport_entries = dict(sorted(passport_entries.items()))

    # Check if content changed (ignoring generated_at)
    generated_at = datetime.now(timezone.utc).isoformat()
    if index_path.exists():
        with open(index_path) as f:
            old_data = json.load(f)
            old_without_timestamp = {k: v for k, v in old_data.items() if k != "generated_at"}
            new_without_timestamp = {
                "schema_version": "1.0.0",
                "disclaimer": DISCLAIMER,
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Derived from Wikipedia (see LICENSE-DATA.md)",
                "passports": passport_entries
            }
            if old_without_timestamp == new_without_timestamp:
                # No change - keep old generated_at
                generated_at = old_data["generated_at"]

    index_data = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "disclaimer": DISCLAIMER,
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "Derived from Wikipedia (see LICENSE-DATA.md)",
        "passports": passport_entries
    }

    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_all_json(
    data_dir: Path,
    all_passports_data: dict[str, list[dict[str, Any]]]
) -> None:
    """
    Write data/all.json with all passport records (minified).

    Args:
        data_dir: Data directory
        all_passports_data: Dict of ISO2 -> records list
    """
    all_path = data_dir / "all.json"

    # Check if content changed (ignoring generated_at)
    generated_at = datetime.now(timezone.utc).isoformat()
    if all_path.exists():
        with open(all_path) as f:
            old_data = json.load(f)
            old_without_timestamp = {k: v for k, v in old_data.items() if k != "generated_at"}
            new_without_timestamp = {
                "schema_version": "1.0.0",
                "disclaimer": DISCLAIMER,
                "license": "CC BY-SA 4.0",
                "attribution": "Derived from Wikipedia (see LICENSE-DATA.md)",
                "passports": dict(sorted(all_passports_data.items()))
            }
            if old_without_timestamp == new_without_timestamp:
                # No change - keep old generated_at
                generated_at = old_data["generated_at"]

    all_data = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "disclaimer": DISCLAIMER,
        "license": "CC BY-SA 4.0",
        "attribution": "Derived from Wikipedia (see LICENSE-DATA.md)",
        "passports": dict(sorted(all_passports_data.items()))
    }

    with open(all_path, "w") as f:
        json.dump(all_data, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")


def write_changelog(
    out_dir: Path,
    all_changes: list[dict[str, Any]]
) -> None:
    """
    Write out/changelog.md with table of changes.

    Args:
        out_dir: Output directory
        all_changes: List of all changes across passports
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "changelog.md", "w") as f:
        f.write("# Changelog\n\n")

        if not all_changes:
            f.write("No changes.\n")
            return

        # Group by passport
        by_passport: dict[str, list[dict[str, Any]]] = {}
        for change in all_changes:
            passport = change["passport"]
            if passport not in by_passport:
                by_passport[passport] = []
            by_passport[passport].append(change)

        for passport in sorted(by_passport.keys()):
            changes = by_passport[passport]
            f.write(f"## {passport}\n\n")

            # Count by type
            added = sum(1 for c in changes if c["change_type"] == "added")
            removed = sum(1 for c in changes if c["change_type"] == "removed")
            changed = sum(1 for c in changes if c["change_type"] == "changed")

            f.write(f"Added: {added}, Removed: {removed}, Changed: {changed}\n\n")

            if changed > 0:
                f.write("| Destination | Area | Old Status | New Status |\n")
                f.write("|------------|------|------------|------------|\n")
                for change in changes:
                    if change["change_type"] == "changed":
                        dest = change["destination_name"]
                        area = change["area"] or ""
                        old = change["old_status"]
                        new = change["new_status"]
                        f.write(f"| {dest} | {area} | {old} | {new} |\n")
                f.write("\n")


def write_report(
    out_dir: Path,
    summary: dict[str, Any]
) -> None:
    """
    Write out/report.md with human-readable summary.

    Args:
        out_dir: Output directory
        summary: Summary dict
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "report.md", "w") as f:
        f.write("# Pipeline Run Report\n\n")

        f.write("## Discovery\n\n")
        f.write(f"- Pages found: {summary['pages_found']}\n")
        f.write(f"- Pages mapped: {summary['pages_mapped']}\n")

        if summary["pages_unmapped"]:
            f.write(f"- Pages unmapped: {len(summary['pages_unmapped'])}\n\n")
            f.write("### Unmapped pages\n\n")
            for page in summary["pages_unmapped"]:
                f.write(f"- {page['title']}: {page['reason']}\n")
            f.write("\n")

        f.write("## Processing\n\n")
        f.write(f"- Pages parsed: {summary['pages_parsed']}\n")
        f.write(f"- Pages skipped (unchanged): {summary['pages_skipped_unchanged']}\n")
        f.write(f"- Total records: {summary['rows']}\n")
        f.write(f"- Total changes: {summary['changes']}\n\n")

        if summary["blocked"]:
            f.write(f"## Blocked ({len(summary['blocked'])})\n\n")
            for blocked in summary["blocked"]:
                f.write(f"- **{blocked['passport']}**: {blocked['reason']}\n")
            f.write("\n")

        if summary["failed"]:
            f.write(f"## Failed ({len(summary['failed'])})\n\n")
            for failed in summary["failed"]:
                f.write(f"- **{failed['passport']}**: {failed['reason']}\n")
            f.write("\n")

        if summary["unmapped_statuses"]:
            f.write(f"## Unmapped Statuses ({len(summary['unmapped_statuses'])})\n\n")
            # Count by raw_status
            status_counts: dict[str, int] = {}
            for item in summary["unmapped_statuses"]:
                raw = item["raw_status"]
                status_counts[raw] = status_counts.get(raw, 0) + 1

            for raw_status in sorted(status_counts.keys(), key=lambda k: status_counts[k], reverse=True):
                count = status_counts[raw_status]
                f.write(f"- `{raw_status}`: {count}\n")
            f.write("\n")

        if summary["unmapped_destinations"]:
            f.write(f"## Unmapped Destinations ({len(summary['unmapped_destinations'])})\n\n")
            for item in summary["unmapped_destinations"]:
                f.write(f"- {item['passport']}: {item['destination_name']} (section: {item['section']})\n")
            f.write("\n")


def write_summary_json(
    out_dir: Path,
    summary: dict[str, Any]
) -> None:
    """
    Write out/summary.json.

    Args:
        out_dir: Output directory
        summary: Summary dict
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")
