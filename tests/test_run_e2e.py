"""End-to-end tests for run() with fake client and parser."""

import json
from unittest.mock import MagicMock
from dataclasses import dataclass

from visa_pipeline.run import run


@dataclass
class FakeParseResult:
    """Fake parse result."""
    records: list
    unmapped_statuses: list
    unmapped_destinations: list
    warnings: list


def make_fake_client():
    """Create a fake WikiClient for testing."""
    client = MagicMock()

    # Default return values for category_members
    client.category_members.side_effect = [
        # First call: main category articles
        ["Visa requirements for German citizens", "Visa requirements for United States citizens"],
        # Second call: main category subcategories
        []
    ]

    # Default return values for revisions
    def fake_revisions(titles):
        result = {}
        for title in titles:
            if title == "Template:Transcluded sections for the visa articles":
                result[title] = {"revid": 1000, "timestamp": "2024-01-01T00:00:00Z"}
            elif "German" in title:
                result[title] = {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"}
            elif "United States" in title:
                result[title] = {"revid": 200, "timestamp": "2024-01-01T00:00:00Z"}
        return result

    client.revisions.side_effect = fake_revisions

    # Default return value for page_wikitext
    client.page_wikitext.return_value = ("template content", 1000)

    return client


def make_fake_parser():
    """Create a fake parser function."""
    def fake_parse_page(wikitext, *, passport, title, revid, transclusions):
        # Return different records based on passport
        if passport == "DE":
            records = [
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
                    "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source_revision": str(revid)
                }
            ]
        elif passport == "US":
            records = [
                {
                    "passport": "US",
                    "destination": "GB",
                    "destination_name": "United Kingdom",
                    "area": None,
                    "status": "visa_free",
                    "alternative_statuses": [],
                    "allowed_stay_days": 180,
                    "allowed_stay_raw": "180 days",
                    "notes": None,
                    "is_territory_or_restricted": False,
                    "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source_revision": str(revid)
                }
            ]
        else:
            records = []

        return FakeParseResult(
            records=records,
            unmapped_statuses=[],
            unmapped_destinations=[],
            warnings=[]
        )

    return fake_parse_page


def test_run_e2e_first_run(tmp_path):
    """Test first run writes files + index + all.json."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    client = make_fake_client()
    parse_page = make_fake_parser()

    exit_code = run(
        data_dir=data_dir,
        state_dir=state_dir,
        out_dir=out_dir,
        client=client,
        parse_page=parse_page
    )

    assert exit_code == 0

    # Check output files exist
    assert (data_dir / "passports" / "DE.json").exists()
    assert (data_dir / "passports" / "US.json").exists()
    assert (data_dir / "index.json").exists()
    assert (data_dir / "all.json").exists()
    assert (out_dir / "summary.json").exists()

    # Check index.json
    with open(data_dir / "index.json") as f:
        index = json.load(f)
    assert "DE" in index["passports"]
    assert "US" in index["passports"]
    assert index["passports"]["DE"]["record_count"] == 1
    assert index["passports"]["US"]["record_count"] == 1

    # Check all.json
    with open(data_dir / "all.json") as f:
        all_data = json.load(f)
    assert "DE" in all_data["passports"]
    assert "US" in all_data["passports"]


def test_run_e2e_unchanged_revids_skips(tmp_path):
    """Test second run with unchanged revids skips and leaves bytes identical."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    client = make_fake_client()
    parse_page = make_fake_parser()

    # First run
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client, parse_page=parse_page)

    # Get file content
    de_file = data_dir / "passports" / "DE.json"
    with open(de_file, "rb") as f:
        de_content_before = f.read()

    # Second run with same client (same revids)
    client2 = make_fake_client()
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client2, parse_page=parse_page)

    # Check file content is identical (byte-for-byte)
    with open(de_file, "rb") as f:
        de_content_after = f.read()

    # Should be unchanged (same bytes)
    assert de_content_after == de_content_before


def test_run_e2e_blocked_passport(tmp_path):
    """Test changed revid with 16 status changes is blocked."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    client = make_fake_client()

    # First parser: creates 20 records with visa_free
    # Use valid ISO2 codes (AA-ZZ range)
    test_codes = [f"{chr(65+i//26)}{chr(65+i%26)}" for i in range(20)]  # AA, AB, AC...

    def first_parser(wikitext, *, passport, title, revid, transclusions):
        if passport == "DE":
            records = [
                {
                    "passport": "DE",
                    "destination": test_codes[i],
                    "destination_name": f"Country {test_codes[i]}",
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
                for i in range(20)
            ]
        else:
            records = []
        return FakeParseResult(records=records, unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    # First run
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client, parse_page=first_parser)

    # Get original file content
    de_file = data_dir / "passports" / "DE.json"
    with open(de_file) as f:
        original_de = json.load(f)

    # Second parser: changes 16 statuses to visa_required
    def second_parser(wikitext, *, passport, title, revid, transclusions):
        if passport == "DE":
            records = [
                {
                    "passport": "DE",
                    "destination": test_codes[i],
                    "destination_name": f"Country {test_codes[i]}",
                    "area": None,
                    "status": "visa_required" if i < 16 else "visa_free",  # 16 changes
                    "alternative_statuses": [],
                    "allowed_stay_days": 90,
                    "allowed_stay_raw": "90 days",
                    "notes": None,
                    "is_territory_or_restricted": False,
                    "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source_revision": str(revid)
                }
                for i in range(20)
            ]
        else:
            records = []
        return FakeParseResult(records=records, unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    # Second run with changed revid
    client2 = MagicMock()
    client2.category_members.side_effect = [
        ["Visa requirements for German citizens", "Visa requirements for United States citizens"],
        []
    ]

    def fake_revisions2(titles):
        result = {}
        for title in titles:
            if title == "Template:Transcluded sections for the visa articles":
                result[title] = {"revid": 1000, "timestamp": "2024-01-01T00:00:00Z"}
            elif "German" in title:
                result[title] = {"revid": 101, "timestamp": "2024-01-02T00:00:00Z"}  # Changed revid
            elif "United States" in title:
                result[title] = {"revid": 200, "timestamp": "2024-01-01T00:00:00Z"}
        return result

    client2.revisions.side_effect = fake_revisions2
    client2.page_wikitext.return_value = ("template content", 1000)

    exit_code = run(
        data_dir=data_dir,
        state_dir=state_dir,
        out_dir=out_dir,
        client=client2,
        parse_page=second_parser,
        max_status_changes=15
    )

    # Should still exit 0 (blocked is not failure)
    assert exit_code == 0

    # Check summary shows it was blocked
    with open(out_dir / "summary.json") as f:
        summary = json.load(f)
    assert len(summary["blocked"]) == 1
    assert summary["blocked"][0]["passport"] == "DE"
    assert "16 status changes" in summary["blocked"][0]["reason"]

    # Check old file is unchanged
    with open(de_file) as f:
        current_de = json.load(f)
    assert current_de["records"] == original_de["records"]

    # Check index carries over old entry
    with open(data_dir / "index.json") as f:
        index = json.load(f)
    assert index["passports"]["DE"]["record_count"] == 20


def test_run_e2e_only_flag_keeps_other_passports(tmp_path):
    """Test --only DE keeps the US entry in index/all.json."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    client = make_fake_client()
    parse_page = make_fake_parser()

    # First run: process both
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client, parse_page=parse_page)

    # Check both exist
    with open(data_dir / "index.json") as f:
        index_before = json.load(f)
    assert "DE" in index_before["passports"]
    assert "US" in index_before["passports"]

    # Second run: only DE
    client2 = MagicMock()
    client2.category_members.side_effect = [
        ["Visa requirements for German citizens", "Visa requirements for United States citizens"],
        []
    ]

    def fake_revisions3(titles):
        result = {}
        for title in titles:
            if title == "Template:Transcluded sections for the visa articles":
                result[title] = {"revid": 1000, "timestamp": "2024-01-01T00:00:00Z"}
            elif "German" in title:
                result[title] = {"revid": 101, "timestamp": "2024-01-02T00:00:00Z"}  # Changed
            elif "United States" in title:
                result[title] = {"revid": 200, "timestamp": "2024-01-01T00:00:00Z"}
        return result

    client2.revisions.side_effect = fake_revisions3
    client2.page_wikitext.return_value = ("template content", 1000)

    run(
        data_dir=data_dir,
        state_dir=state_dir,
        out_dir=out_dir,
        client=client2,
        parse_page=parse_page,
        only=["DE"]
    )

    # Check US is still in index and all.json
    with open(data_dir / "index.json") as f:
        index_after = json.load(f)
    assert "DE" in index_after["passports"]
    assert "US" in index_after["passports"]  # Should still be there!

    with open(data_dir / "all.json") as f:
        all_data = json.load(f)
    assert "US" in all_data["passports"]  # Should still be there!


def test_run_e2e_zero_rows_exit_1(tmp_path):
    """Test zero rows where previous had data -> exit 1 and old file kept."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    client = make_fake_client()
    parse_page = make_fake_parser()

    # First run: create data
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client, parse_page=parse_page)

    # Get original data
    de_file = data_dir / "passports" / "DE.json"
    with open(de_file) as f:
        original_data = json.load(f)
    assert len(original_data["records"]) > 0

    # Second run: parser returns zero records
    def zero_parser(wikitext, *, passport, title, revid, transclusions):
        return FakeParseResult(records=[], unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    client2 = MagicMock()
    client2.category_members.side_effect = [
        ["Visa requirements for German citizens", "Visa requirements for United States citizens"],
        []
    ]

    def fake_revisions4(titles):
        result = {}
        for title in titles:
            if title == "Template:Transcluded sections for the visa articles":
                result[title] = {"revid": 1000, "timestamp": "2024-01-01T00:00:00Z"}
            elif "German" in title:
                result[title] = {"revid": 101, "timestamp": "2024-01-02T00:00:00Z"}  # Changed
            elif "United States" in title:
                result[title] = {"revid": 200, "timestamp": "2024-01-01T00:00:00Z"}
        return result

    client2.revisions.side_effect = fake_revisions4
    client2.page_wikitext.return_value = ("template content", 1000)

    exit_code = run(
        data_dir=data_dir,
        state_dir=state_dir,
        out_dir=out_dir,
        client=client2,
        parse_page=zero_parser
    )

    # Should exit 1 (failure)
    assert exit_code == 1

    # Check summary shows failure
    with open(out_dir / "summary.json") as f:
        summary = json.load(f)
    assert len(summary["failed"]) == 2  # Both DE and US fail
    assert any(f["passport"] == "DE" and "zero records" in f["reason"] for f in summary["failed"])

    # Check old file is kept unchanged
    with open(de_file) as f:
        current_data = json.load(f)
    assert current_data["records"] == original_data["records"]


def test_run_e2e_transclusions_passed_to_parser(tmp_path):
    """Test transclusions passed to parse_page on a run where only a page changed."""
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"

    # Track what transclusions were passed to parser
    transcl_calls = []

    def tracking_parser(wikitext, *, passport, title, revid, transclusions):
        transcl_calls.append({"passport": passport, "transclusions": transclusions})
        records = []
        if passport == "DE":
            records = [{
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
                "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "source_revision": str(revid)
            }]
        elif passport == "US":
            # Give US records too to avoid "no rows parsed" failure
            records = [{
                "passport": "US",
                "destination": "GB",
                "destination_name": "United Kingdom",
                "area": None,
                "status": "visa_free",
                "alternative_statuses": [],
                "allowed_stay_days": 180,
                "allowed_stay_raw": "180 days",
                "notes": None,
                "is_territory_or_restricted": False,
                "source_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "source_revision": str(revid)
            }]
        return FakeParseResult(records=records, unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    # First run with template fetch
    client = make_fake_client()
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client, parse_page=tracking_parser)

    # Clear tracking
    transcl_calls.clear()

    # Second run: only DE changed, template unchanged
    client2 = MagicMock()
    client2.category_members.side_effect = [
        ["Visa requirements for German citizens", "Visa requirements for United States citizens"],
        []
    ]

    def fake_revisions5(titles):
        result = {}
        for title in titles:
            if title == "Template:Transcluded sections for the visa articles":
                result[title] = {"revid": 1000, "timestamp": "2024-01-01T00:00:00Z"}  # Unchanged
            elif "German" in title:
                result[title] = {"revid": 101, "timestamp": "2024-01-02T00:00:00Z"}  # Changed
            elif "United States" in title:
                result[title] = {"revid": 200, "timestamp": "2024-01-01T00:00:00Z"}  # Unchanged
        return result

    client2.revisions.side_effect = fake_revisions5
    client2.page_wikitext.return_value = ("template content", 1000)

    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, client=client2, parse_page=tracking_parser)

    # Check that transclusions were passed to DE (which changed)
    de_calls = [c for c in transcl_calls if c["passport"] == "DE"]
    assert len(de_calls) == 1
    # transclusions should be a dict (parsed template), not empty
    assert isinstance(de_calls[0]["transclusions"], dict)
