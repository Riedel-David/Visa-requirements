"""Tests for publishing."""

import json

import pytest

from visa_pipeline.publish import (
    format_passport_data,
    write_passport_file,
    write_index_json,
    DISCLAIMER
)


@pytest.fixture
def sample_records():
    """Sample visa requirement records."""
    return [
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


def test_format_passport_data(sample_records):
    """Test passport data formatting."""
    data = format_passport_data(
        passport="DE",
        title="Visa requirements for German citizens",
        revid=123456,
        timestamp="2024-01-01T00:00:00Z",
        records=sample_records
    )

    assert data["passport"] == "DE"
    assert data["schema_version"] == "1.0.0"
    assert data["source_revision"] == "123456"
    assert len(data["records"]) == 1
    assert "generated_at" in data


def test_format_passport_data_sorts_records():
    """Test records are sorted by destination then area."""
    records = [
        {
            "passport": "DE",
            "destination": "US",
            "destination_name": "United States",
            "area": "Guam",
            "status": "visa_free",
            "alternative_statuses": [],
            "allowed_stay_days": None,
            "allowed_stay_raw": None,
            "notes": None,
            "is_territory_or_restricted": True,
            "source_url": "https://example.com",
            "source_revision": "123"
        },
        {
            "passport": "DE",
            "destination": "US",
            "destination_name": "United States",
            "area": None,
            "status": "visa_free",
            "alternative_statuses": [],
            "allowed_stay_days": 90,
            "allowed_stay_raw": "90 days",
            "notes": None,
            "is_territory_or_restricted": False,
            "source_url": "https://example.com",
            "source_revision": "123"
        },
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
            "source_url": "https://example.com",
            "source_revision": "123"
        }
    ]

    data = format_passport_data(
        passport="DE",
        title="Test",
        revid=123,
        timestamp="2024-01-01T00:00:00Z",
        records=records
    )

    # Should be sorted: FR (null area), US (null area), US (Guam)
    assert data["records"][0]["destination"] == "FR"
    assert data["records"][1]["destination"] == "US"
    assert data["records"][1]["area"] is None
    assert data["records"][2]["destination"] == "US"
    assert data["records"][2]["area"] == "Guam"


def test_write_passport_file_new(tmp_path, sample_records):
    """Test writing new passport file."""
    data = format_passport_data(
        passport="DE",
        title="Test",
        revid=123,
        timestamp="2024-01-01T00:00:00Z",
        records=sample_records
    )

    changed = write_passport_file(tmp_path, data)

    assert changed
    assert (tmp_path / "passports" / "DE.json").exists()


def test_write_passport_file_unchanged(tmp_path, sample_records):
    """Test writing unchanged passport file."""
    data = format_passport_data(
        passport="DE",
        title="Test",
        revid=123,
        timestamp="2024-01-01T00:00:00Z",
        records=sample_records
    )

    # Write first time
    write_passport_file(tmp_path, data)

    # Write again with same data (different generated_at)
    data2 = format_passport_data(
        passport="DE",
        title="Test",
        revid=123,
        timestamp="2024-01-01T00:00:00Z",
        records=sample_records
    )

    changed = write_passport_file(tmp_path, data2, previous_data=data)

    assert not changed


def test_write_passport_file_changed(tmp_path, sample_records):
    """Test writing changed passport file."""
    data = format_passport_data(
        passport="DE",
        title="Test",
        revid=123,
        timestamp="2024-01-01T00:00:00Z",
        records=sample_records
    )

    write_passport_file(tmp_path, data)

    # Modify data (a new revision alone would not count as a change)
    changed_records = [dict(r) for r in sample_records]
    changed_records[0]["status"] = "evisa"
    data2 = format_passport_data(
        passport="DE",
        title="Test",
        revid=124,
        timestamp="2024-01-02T00:00:00Z",
        records=changed_records
    )

    changed = write_passport_file(tmp_path, data2, previous_data=data)

    assert changed


def test_write_index_json(tmp_path):
    """Test writing index.json."""
    passports = {
        "DE": {
            "title": "Visa requirements for German citizens",
            "revid": 123,
            "timestamp": "2024-01-01T00:00:00Z",
            "record_count": 193,
            "last_changed": "2024-01-01T00:00:00Z"
        }
    }

    write_index_json(tmp_path, passports, {})

    index_file = tmp_path / "index.json"
    assert index_file.exists()

    with open(index_file) as f:
        data = json.load(f)

    assert data["schema_version"] == "1.0.0"
    assert data["disclaimer"] == DISCLAIMER
    assert "DE" in data["passports"]
    assert data["passports"]["DE"]["record_count"] == 193


def test_write_index_json_carries_over_blocked(tmp_path):
    """Test index.json carries over blocked passports."""
    # Write initial index
    passports = {
        "DE": {
            "title": "Visa requirements for German citizens",
            "revid": 123,
            "timestamp": "2024-01-01T00:00:00Z",
            "record_count": 193,
            "last_changed": "2024-01-01T00:00:00Z"
        }
    }
    write_index_json(tmp_path, passports, {})

    # Update with DE blocked
    blocked = {
        "DE": {
            "title": "Visa requirements for German citizens",
            "revid": 124,
            "timestamp": "2024-01-02T00:00:00Z",
            "record_count": 0
        }
    }
    write_index_json(tmp_path, {}, blocked)

    # Should keep old entry
    with open(tmp_path / "index.json") as f:
        data = json.load(f)

    assert data["passports"]["DE"]["source_revision"] == "123"
