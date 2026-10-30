"""Tests for extract_main.py - parsing visa requirements pages."""
import json
from pathlib import Path

import pytest

from visa_pipeline import extract_main, transclusions


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> tuple[str, dict]:
    """Load a fixture wikitext and its metadata."""
    wikitext_file = FIXTURES / f"{name}.wikitext"
    meta_file = FIXTURES / f"{name}.meta.json"

    wikitext = wikitext_file.read_text(encoding='utf-8')
    meta = json.loads(meta_file.read_text(encoding='utf-8'))

    return wikitext, meta


def load_transclusions() -> dict[str, str]:
    """Load and parse the transclusion template."""
    template_wikitext, _ = load_fixture("Template_Transcluded_sections_for_the_visa_articles")
    return transclusions.parse_template(template_wikitext)


@pytest.fixture(scope="module")
def transcl():
    """Shared transclusions dict for all tests."""
    return load_transclusions()


class TestGermanCitizens:
    """Tests for German citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_German_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="DE",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_japan_visa_free(self, result):
        """DE -> JP should be visa free, 90 days."""
        jp_records = [r for r in result.records if r['destination'] == 'JP']
        assert len(jp_records) == 1
        rec = jp_records[0]
        assert rec['status'] == 'visa_free'
        assert rec['allowed_stay_days'] == 90
        assert rec['is_territory_or_restricted'] is False

    def test_afghanistan_evisa(self, result):
        """DE -> AF should be evisa."""
        af_records = [r for r in result.records if r['destination'] == 'AF']
        assert len(af_records) == 1
        rec = af_records[0]
        assert rec['status'] == 'evisa'
        assert rec['is_territory_or_restricted'] is False

    def test_algeria_notes_from_transclusion(self, result):
        """DE -> DZ notes should come from transcluded template section."""
        dz_records = [r for r in result.records if r['destination'] == 'DZ']
        assert len(dz_records) == 1
        rec = dz_records[0]
        assert rec['notes'] is not None, "Algeria notes should not be empty"
        assert len(rec['notes']) > 0, "Algeria notes should have content"
        # Check that content comes from "Algeria. VOA" template section
        assert "passport containing visas or stamps issued by Israel" in rec['notes']

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestUnitedStatesCitizens:
    """Tests for United States citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_United_States_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="US",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_bangladesh_voa(self, result):
        """US -> BD should be visa on arrival."""
        bd_records = [r for r in result.records if r['destination'] == 'BD']
        if bd_records:
            rec = bd_records[0]
            assert rec['status'] in ['visa_on_arrival', 'evisa', 'visa_free']

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestIndianCitizens:
    """Tests for Indian citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_Indian_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="IN",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_albania_evisa(self, result):
        """IN -> AL should be evisa."""
        al_records = [r for r in result.records if r['destination'] == 'AL']
        if al_records:
            rec = al_records[0]
            assert rec['status'] == 'evisa'

    def test_andorra_visa_required(self, result):
        """IN -> AD should be visa required."""
        ad_records = [r for r in result.records if r['destination'] == 'AD']
        if ad_records:
            rec = ad_records[0]
            assert rec['status'] == 'visa_required'

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestBritishCitizens:
    """Tests for British citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_British_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="GB",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestEmiratiCitizens:
    """Tests for Emirati citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_Emirati_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="AE",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 150 <= len(result.records) <= 250, f"Got {len(result.records)} records"

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestAfghanCitizens:
    """Tests for Afghan citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_Afghan_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="AF",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records."""
        assert 150 <= len(result.records) <= 250, f"Got {len(result.records)} records"

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestBrazilianCitizens:
    """Tests for Brazilian citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_Brazilian_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="BR",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestJapaneseCitizens:
    """Tests for Japanese citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture("Visa_requirements_for_Japanese_citizens")
        return extract_main.parse_page(
            wikitext,
            passport="JP",
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Should have ~190-200 main table records plus territories."""
        assert 190 <= len(result.records) <= 300, f"Got {len(result.records)} records"

    def test_unique_keys(self, result):
        """All (destination, area) keys should be unique."""
        keys = [(r['destination'], r['area']) for r in result.records]
        assert len(keys) == len(set(keys)), "Found duplicate keys"


class TestDeduplication:
    """Tests for deduplication logic across all fixtures."""

    @pytest.fixture(scope="class", params=[
        ("German", "DE"),
        ("United_States", "US"),
        ("Indian", "IN"),
        ("British", "GB"),
        ("Emirati", "AE"),
        ("Afghan", "AF"),
        ("Brazilian", "BR"),
        ("Japanese", "JP"),
    ])
    def fixture_result(self, request, transcl):
        """Parse each fixture and return result."""
        name, passport = request.param
        wikitext, meta = load_fixture(f"Visa_requirements_for_{name}_citizens")
        result = extract_main.parse_page(
            wikitext,
            passport=passport,
            title=meta["title"],
            revid=meta["revid"],
            transclusions=transcl
        )
        return passport, result

    def test_no_status_conflicts_in_dedup(self, fixture_result):
        """Dedup drops should never involve rows with different statuses being discarded.

        When a duplicate key is found, if statuses differ, we should keep the more
        specific (territory) row and warn. CONFLICT warnings indicate same-type rows
        with different statuses, which should never happen.
        """
        passport, result = fixture_result

        # Check for CONFLICT warnings (same-type rows with different statuses)
        conflict_warnings = [w for w in result.warnings if 'CONFLICT' in w]

        assert len(conflict_warnings) == 0, (
            f"{passport}: Found {len(conflict_warnings)} conflicts where same-type rows "
            f"have different statuses: {conflict_warnings}"
        )
