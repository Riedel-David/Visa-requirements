"""Tests for main pipeline run."""

import json
from pathlib import Path
from unittest.mock import Mock
from dataclasses import dataclass

from visa_pipeline.run import run, needs_update


@dataclass
class FakeParseResult:
    """Fake parse result."""
    records: list
    unmapped_statuses: list
    unmapped_destinations: list
    warnings: list


def test_needs_update_force():
    """Test needs_update with force flag."""
    assert needs_update("DE", 123, {}, Path("."), force=True)


def test_needs_update_missing_output():
    """Test needs_update when output file missing."""
    tmp = Path("/tmp/nonexistent")
    assert needs_update("DE", 123, {}, tmp, force=False)


def test_needs_update_revid_changed():
    """Test needs_update when revid changed."""
    stored = {"DE": {"revid": 122, "timestamp": "2024-01-01T00:00:00Z"}}
    assert needs_update("DE", 123, stored, Path("."), force=False)


def test_needs_update_unchanged(tmp_path):
    """Test needs_update when unchanged."""
    # Create output file
    output_dir = tmp_path / "passports"
    output_dir.mkdir()
    (output_dir / "DE.json").write_text("{}")

    stored = {"DE": {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}}
    assert not needs_update("DE", 123, stored, tmp_path, force=False)


def test_run_end_to_end(tmp_path):
    """Test end-to-end pipeline run with fake client and parser."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    # Create fake client
    fake_client = Mock()

    def fake_category_members(category, namespace=0):
        if namespace == 0:
            return ["Visa requirements for German citizens"]
        else:
            return []

    fake_client.category_members.side_effect = fake_category_members

    fake_client.revisions.return_value = {
        "Visa requirements for German citizens": {
            "revid": 123,
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "Template:Transcluded sections for the visa articles": {
            "revid": 456,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }

    fake_client.page_wikitext.return_value = ("== Section ==\nContent", 123)

    # Create fake parser
    def fake_parse_page(wikitext, *, passport, title, revid, transclusions):
        return FakeParseResult(
            records=[
                {
                    "passport": passport,
                    "destination": "FR",
                    "destination_name": "France",
                    "area": None,
                    "status": "visa_free",
                    "alternative_statuses": [],
                    "allowed_stay_days": 90,
                    "allowed_stay_raw": "90 days",
                    "notes": None,
                    "is_territory_or_restricted": False,
                    "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source_revision": str(revid)
                }
            ],
            unmapped_statuses=[],
            unmapped_destinations=[],
            warnings=[]
        )

    # Patch the run function to use our fake client
    from visa_pipeline import run as run_module

    original_client = run_module.WikiClient

    try:
        # Mock WikiClient
        run_module.WikiClient = lambda min_interval: fake_client

        # Mock discover.get_pages
        from visa_pipeline import discover

        original_get_pages = discover.get_pages

        def fake_get_pages(client, state_dir, overrides_path, refresh=False):
            return [
                {
                    "title": "Visa requirements for German citizens",
                    "passport": "DE",
                    "reason": "demonym mapping"
                }
            ]

        discover.get_pages = fake_get_pages

        # Run pipeline
        exit_code = run(
            data_dir=data_dir,
            state_dir=state_dir,
            out_dir=out_dir,
            parse_page=fake_parse_page
        )

        assert exit_code == 0

        # Check output files
        assert (data_dir / "passports" / "DE.json").exists()
        assert (data_dir / "index.json").exists()
        assert (data_dir / "all.json").exists()
        assert (out_dir / "summary.json").exists()
        assert (out_dir / "report.md").exists()
        assert (out_dir / "changelog.md").exists()

        # Check passport file content
        with open(data_dir / "passports" / "DE.json") as f:
            passport_data = json.load(f)

        assert passport_data["passport"] == "DE"
        assert len(passport_data["records"]) == 1
        assert passport_data["records"][0]["destination"] == "FR"

        # Check summary
        with open(out_dir / "summary.json") as f:
            summary = json.load(f)

        assert summary["pages_found"] == 1
        assert summary["pages_parsed"] == 1
        assert summary["rows"] == 1

    finally:
        # Restore
        run_module.WikiClient = original_client
        discover.get_pages = original_get_pages


def test_run_with_blocked_passport(tmp_path):
    """Test run with passport blocked by safety check."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    # Create existing data with many records
    existing_dir = data_dir / "passports"
    existing_dir.mkdir(parents=True)

    existing_data = {
        "schema_version": "1.0.0",
        "passport": "DE",
        "source_title": "Test",
        "source_url": "https://example.com",
        "source_revision": "122",
        "source_timestamp": "2024-01-01T00:00:00Z",
        "generated_at": "2024-01-01T00:00:00Z",
        "license": "CC BY-SA 4.0",
        "attribution": "Test",
        "records": [
            {
                "passport": "DE",
                "destination": f"C{i:02d}",
                "destination_name": f"Country {i}",
                "area": None,
                "status": "visa_free",
                "alternative_statuses": [],
                "allowed_stay_days": 90,
                "allowed_stay_raw": "90 days",
                "notes": None,
                "is_territory_or_restricted": False,
                "source_url": "https://example.com",
                "source_revision": "122"
            }
            for i in range(20)
        ]
    }

    with open(existing_dir / "DE.json", "w") as f:
        json.dump(existing_data, f)

    # Create fake client
    fake_client = Mock()

    def fake_category_members(category, namespace=0):
        if namespace == 0:
            return ["Visa requirements for German citizens"]
        else:
            return []

    fake_client.category_members.side_effect = fake_category_members

    fake_client.revisions.return_value = {
        "Visa requirements for German citizens": {
            "revid": 123,
            "timestamp": "2024-01-02T00:00:00Z"
        },
        "Template:Transcluded sections for the visa articles": {
            "revid": 456,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }

    fake_client.page_wikitext.return_value = ("== Section ==\nContent", 123)

    # Create fake parser that changes too many statuses
    def fake_parse_page(wikitext, *, passport, title, revid, transclusions):
        records = []
        for i in range(20):
            records.append({
                "passport": passport,
                "destination": f"C{i:02d}",
                "destination_name": f"Country {i}",
                "area": None,
                "status": "visa_required" if i < 16 else "visa_free",  # 16 changes
                "alternative_statuses": [],
                "allowed_stay_days": 90,
                "allowed_stay_raw": "90 days",
                "notes": None,
                "is_territory_or_restricted": False,
                "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "source_revision": str(revid)
            })

        return FakeParseResult(
            records=records,
            unmapped_statuses=[],
            unmapped_destinations=[],
            warnings=[]
        )

    # Patch and run
    from visa_pipeline import run as run_module
    from visa_pipeline import discover

    original_client = run_module.WikiClient
    original_get_pages = discover.get_pages

    try:
        run_module.WikiClient = lambda min_interval: fake_client

        def fake_get_pages(client, state_dir, overrides_path, refresh=False):
            return [
                {
                    "title": "Visa requirements for German citizens",
                    "passport": "DE",
                    "reason": "demonym mapping"
                }
            ]

        discover.get_pages = fake_get_pages

        exit_code = run(
            data_dir=data_dir,
            state_dir=state_dir,
            out_dir=out_dir,
            parse_page=fake_parse_page,
            max_status_changes=15
        )

        # Should still exit 0 (blocked is not a failure)
        assert exit_code == 0

        # Check summary
        with open(out_dir / "summary.json") as f:
            summary = json.load(f)

        assert len(summary["blocked"]) == 1
        assert summary["blocked"][0]["passport"] == "DE"
        assert "16 status changes" in summary["blocked"][0]["reason"]

    finally:
        run_module.WikiClient = original_client
        discover.get_pages = original_get_pages
