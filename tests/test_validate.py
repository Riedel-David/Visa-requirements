"""Tests for validation."""

import json
from pathlib import Path

import pytest
import jsonschema

from visa_pipeline.validate import (
    validate_passport_file,
    check_safety,
    get_changes_for_changelog
)


@pytest.fixture
def schema():
    """Load test schema."""
    schema_path = Path(__file__).parent.parent / "src" / "visa_pipeline" / "schema" / "passport.schema.json"
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def valid_passport_data():
    """Valid passport data."""
    return {
        "schema_version": "1.0.0",
        "passport": "DE",
        "source_title": "Visa requirements for German citizens",
        "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
        "source_revision": "123456",
        "source_timestamp": "2024-01-01T00:00:00Z",
        "generated_at": "2024-01-01T00:00:00Z",
        "license": "CC BY-SA 4.0",
        "attribution": "Derived from Wikipedia",
        "records": [
            {
                "passport": "DE",
                "destination": "FR",
                "destination_name": "France",
                "area": None,
                "status": "visa_free",
                "alternative_statuses": [],
                "allowed_stay_days": 90,
                "allowed_stay_raw": "90 days",
                "notes": None,
                "is_territory_or_restricted": False,
                "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
                "source_revision": "123456"
            }
        ]
    }


def test_validate_passport_file_valid(schema, valid_passport_data):
    """Test validation of valid passport data."""
    validate_passport_file(valid_passport_data, schema)


def test_validate_passport_file_invalid_status(schema, valid_passport_data):
    """Test validation rejects invalid status."""
    valid_passport_data["records"][0]["status"] = "invalid_status"

    with pytest.raises(jsonschema.ValidationError):
        validate_passport_file(valid_passport_data, schema)


def test_validate_passport_file_missing_field(schema, valid_passport_data):
    """Test validation rejects missing required field."""
    del valid_passport_data["records"][0]["destination"]

    with pytest.raises(jsonschema.ValidationError):
        validate_passport_file(valid_passport_data, schema)


def test_validate_passport_file_extra_field(schema, valid_passport_data):
    """Test validation rejects extra fields."""
    valid_passport_data["records"][0]["extra_field"] = "value"

    with pytest.raises(jsonschema.ValidationError):
        validate_passport_file(valid_passport_data, schema)


def test_check_safety_first_run(valid_passport_data):
    """Test safety check passes for first run."""
    is_safe, reason = check_safety(valid_passport_data, None, 15, 10)

    assert is_safe
    assert reason is None


def test_check_safety_zero_records_fails(valid_passport_data):
    """Test safety check fails when new data has zero records."""
    previous = valid_passport_data.copy()
    new_data = valid_passport_data.copy()
    new_data["records"] = []

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert not is_safe
    assert "zero records" in reason


def test_check_safety_record_drop_blocked(valid_passport_data):
    """Test safety check blocks large record drops."""
    previous = valid_passport_data.copy()
    previous["records"] = [previous["records"][0].copy() for _ in range(100)]

    new_data = valid_passport_data.copy()
    new_data["records"] = previous["records"][:88]  # 12% drop

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert not is_safe
    assert "dropped" in reason


def test_check_safety_record_drop_allowed(valid_passport_data):
    """Test safety check allows small record drops."""
    previous = valid_passport_data.copy()
    previous["records"] = [previous["records"][0].copy() for _ in range(100)]

    new_data = valid_passport_data.copy()
    new_data["records"] = previous["records"][:91]  # 9% drop

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert is_safe


def test_check_safety_status_changes_blocked(valid_passport_data):
    """Test safety check blocks too many status changes."""
    previous = valid_passport_data.copy()
    previous["records"] = [previous["records"][0].copy() for _ in range(20)]
    for i, rec in enumerate(previous["records"]):
        rec["destination"] = f"C{i:02d}"

    new_data = valid_passport_data.copy()
    new_data["records"] = [rec.copy() for rec in previous["records"]]

    # Change 16 statuses
    for i in range(16):
        new_data["records"][i]["status"] = "visa_required"

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert not is_safe
    assert "16 status changes" in reason


def test_check_safety_status_changes_allowed(valid_passport_data):
    """Test safety check allows acceptable status changes."""
    previous = valid_passport_data.copy()
    previous["records"] = [previous["records"][0].copy() for _ in range(20)]
    for i, rec in enumerate(previous["records"]):
        rec["destination"] = f"C{i:02d}"

    new_data = valid_passport_data.copy()
    new_data["records"] = [rec.copy() for rec in previous["records"]]

    # Change 15 statuses (at limit)
    for i in range(15):
        new_data["records"][i]["status"] = "visa_required"

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert is_safe


def test_check_safety_additions_not_counted(valid_passport_data):
    """Test that additions don't count as status changes."""
    previous = valid_passport_data.copy()

    new_data = valid_passport_data.copy()
    new_record = previous["records"][0].copy()
    new_record["destination"] = "ES"
    new_data["records"].append(new_record)

    is_safe, reason = check_safety(new_data, previous, 15, 10)

    assert is_safe


def test_get_changes_for_changelog_added(valid_passport_data):
    """Test changelog detects additions."""
    previous = valid_passport_data.copy()
    previous["records"] = []

    new_data = valid_passport_data.copy()

    changes = get_changes_for_changelog(new_data, previous)

    assert len(changes) == 1
    assert changes[0]["change_type"] == "added"
    assert changes[0]["destination"] == "FR"


def test_get_changes_for_changelog_removed(valid_passport_data):
    """Test changelog detects removals."""
    previous = valid_passport_data.copy()

    new_data = valid_passport_data.copy()
    new_data["records"] = []

    changes = get_changes_for_changelog(new_data, previous)

    assert len(changes) == 1
    assert changes[0]["change_type"] == "removed"
    assert changes[0]["old_status"] == "visa_free"


def test_get_changes_for_changelog_changed(valid_passport_data):
    """Test changelog detects status changes."""
    previous = valid_passport_data.copy()

    new_data = valid_passport_data.copy()
    new_data["records"][0]["status"] = "visa_required"

    changes = get_changes_for_changelog(new_data, previous)

    assert len(changes) == 1
    assert changes[0]["change_type"] == "changed"
    assert changes[0]["old_status"] == "visa_free"
    assert changes[0]["new_status"] == "visa_required"
