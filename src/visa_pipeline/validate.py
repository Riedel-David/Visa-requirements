"""Validation and safety checks."""

import json
from pathlib import Path
from typing import Any

import jsonschema


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load JSON Schema from file."""
    with open(schema_path) as f:
        return json.load(f)


def validate_passport_file(data: dict[str, Any], schema: dict[str, Any]) -> None:
    """
    Validate passport data against JSON Schema.

    Args:
        data: Passport data dict
        schema: JSON Schema dict

    Raises:
        jsonschema.ValidationError: If validation fails
    """
    jsonschema.validate(instance=data, schema=schema)


def load_previous_passport(data_dir: Path, iso2: str) -> dict[str, Any] | None:
    """
    Load previous passport data for diff comparison.

    Args:
        data_dir: Data directory path
        iso2: Passport ISO2 code

    Returns:
        Previous data dict or None if not found
    """
    file_path = data_dir / "passports" / f"{iso2}.json"
    if not file_path.exists():
        return None

    with open(file_path) as f:
        return json.load(f)


def check_safety(
    new_data: dict[str, Any],
    previous_data: dict[str, Any] | None,
    max_status_changes: int,
    max_record_drop_pct: int
) -> tuple[bool, str | None]:
    """
    Check if changes are within safety thresholds.

    Args:
        new_data: New passport data
        previous_data: Previous passport data (or None for first run)
        max_status_changes: Maximum allowed status changes
        max_record_drop_pct: Maximum allowed record count drop percentage

    Returns:
        Tuple of (is_safe, reason). If not safe, reason explains why.
    """
    # First run - always safe
    if previous_data is None:
        return True, None

    new_records = new_data["records"]
    old_records = previous_data["records"]

    # Zero records where previous had records - FAIL
    if len(new_records) == 0 and len(old_records) > 0:
        return False, f"zero records (previous: {len(old_records)})"

    # Check record count drop
    if len(old_records) > 0:
        drop_pct = ((len(old_records) - len(new_records)) / len(old_records)) * 100
        if drop_pct > max_record_drop_pct:
            return False, f"record count dropped {drop_pct:.1f}% ({len(old_records)} -> {len(new_records)})"

    # Build old record map by key
    old_map = {}
    for rec in old_records:
        key = (rec["destination"], rec["area"])
        old_map[key] = rec

    # Count status changes (not additions/removals)
    status_changes = 0
    for new_rec in new_records:
        key = (new_rec["destination"], new_rec["area"])
        if key in old_map:
            old_status = old_map[key]["status"]
            new_status = new_rec["status"]
            if old_status != new_status:
                status_changes += 1

    if status_changes > max_status_changes:
        return False, f"{status_changes} status changes (max: {max_status_changes})"

    return True, None


def get_changes_for_changelog(
    new_data: dict[str, Any],
    previous_data: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """
    Get list of changes for changelog.

    Args:
        new_data: New passport data
        previous_data: Previous passport data (or None)

    Returns:
        List of change records: {passport, destination, area, old_status, new_status, change_type}
        change_type is one of: added, removed, changed
    """
    if previous_data is None:
        return []

    passport = new_data["passport"]
    new_records = new_data["records"]
    old_records = previous_data["records"]

    # Build maps
    old_map = {}
    for rec in old_records:
        key = (rec["destination"], rec["area"])
        old_map[key] = rec

    new_map = {}
    for rec in new_records:
        key = (rec["destination"], rec["area"])
        new_map[key] = rec

    changes = []

    # Find additions and changes
    for key, new_rec in new_map.items():
        if key not in old_map:
            changes.append({
                "passport": passport,
                "destination": new_rec["destination"],
                "destination_name": new_rec["destination_name"],
                "area": new_rec["area"],
                "old_status": None,
                "new_status": new_rec["status"],
                "change_type": "added"
            })
        elif old_map[key]["status"] != new_rec["status"]:
            changes.append({
                "passport": passport,
                "destination": new_rec["destination"],
                "destination_name": new_rec["destination_name"],
                "area": new_rec["area"],
                "old_status": old_map[key]["status"],
                "new_status": new_rec["status"],
                "change_type": "changed"
            })

    # Find removals
    for key, old_rec in old_map.items():
        if key not in new_map:
            changes.append({
                "passport": passport,
                "destination": old_rec["destination"],
                "destination_name": old_rec["destination_name"],
                "area": old_rec["area"],
                "old_status": old_rec["status"],
                "new_status": None,
                "change_type": "removed"
            })

    return changes
