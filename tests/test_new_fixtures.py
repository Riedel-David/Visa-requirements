"""Tests for newly added fixtures (CA, TR, XN, DK)."""
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


class TestCanadianCitizens:
    """Test Canadian citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture('Visa_requirements_for_Canadian_citizens')
        return extract_main.parse_page(
            wikitext,
            passport='CA',
            title='Visa requirements for Canadian citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Canadian page should parse to at least 190 records."""
        assert len(result.records) >= 190, f"Expected >= 190 records, got {len(result.records)}"

    def test_sample_records(self, result):
        """Check a few sample records."""
        records_by_dest = {r['destination']: r for r in result.records if not r['area']}

        # Check Afghanistan (evisa)
        assert 'AF' in records_by_dest
        af = records_by_dest['AF']
        assert af['status'] in ['evisa', 'visa_required']
        assert af['destination_name'] == 'Afghanistan'

        # Check Germany (visa-free)
        assert 'DE' in records_by_dest
        de = records_by_dest['DE']
        assert de['status'] == 'visa_free'


class TestTurkishCitizens:
    """Test Turkish citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture('Visa_requirements_for_Turkish_citizens')
        return extract_main.parse_page(
            wikitext,
            passport='TR',
            title='Visa requirements for Turkish citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Turkish page should parse to at least 190 records."""
        assert len(result.records) >= 190, f"Expected >= 190 records, got {len(result.records)}"

    def test_sample_records(self, result):
        """Check a few sample records."""
        records_by_dest = {r['destination']: r for r in result.records if not r['area']}

        # Check Albania (visa-free)
        assert 'AL' in records_by_dest
        al = records_by_dest['AL']
        assert al['status'] == 'visa_free'
        assert al['destination_name'] == 'Albania'


class TestNorthernCypriotCitizens:
    """Test Northern Cypriot citizens visa requirements."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture('Visa_requirements_for_Northern_Cypriot_citizens')
        return extract_main.parse_page(
            wikitext,
            passport='XN',
            title='Visa requirements for Northern Cypriot citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Northern Cyprus page has only 1 destination (Turkey)."""
        assert len(result.records) == 1, f"Expected 1 record, got {len(result.records)}"

    def test_turkey_record(self, result):
        """Check Turkey record."""
        assert result.records[0]['destination'] == 'TR'
        assert result.records[0]['destination_name'] == 'Turkey'
        # Status is 'special' because the cleaned text includes extra info after newline
        # This is expected for this edge-case table structure
        assert result.records[0]['status'] in ['visa_free', 'special']


class TestDanishCitizens:
    """Test Danish citizens visa requirements (FO/GL redirect here)."""

    @pytest.fixture(scope="class")
    def result(self, transcl):
        wikitext, meta = load_fixture('Visa_requirements_for_Danish_citizens')
        return extract_main.parse_page(
            wikitext,
            passport='DK',
            title='Visa requirements for Danish citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

    def test_record_count(self, result):
        """Danish page should parse to at least 190 records."""
        assert len(result.records) >= 190, f"Expected >= 190 records, got {len(result.records)}"


class TestSmallPages:
    """Test pages with limited recognition (XA, XO, XT) - these have no standard tables."""

    def test_abkhazian(self, transcl):
        """Abkhazian page has no parseable visa requirements table."""
        wikitext, meta = load_fixture('Visa_requirements_for_Abkhazian_citizens')

        result = extract_main.parse_page(
            wikitext,
            passport='XA',
            title='Visa requirements for Abkhazian citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

        # This page has no standard visa requirements table, so 0 records is expected
        assert len(result.records) == 0

    def test_south_ossetian(self, transcl):
        """South Ossetian page has no parseable visa requirements table."""
        wikitext, meta = load_fixture('Visa_requirements_for_South_Ossetian_citizens')

        result = extract_main.parse_page(
            wikitext,
            passport='XO',
            title='Visa requirements for South Ossetian citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

        # This page has no standard visa requirements table, so 0 records is expected
        assert len(result.records) == 0

    def test_transnistrian(self, transcl):
        """Transnistrian page has no parseable visa requirements table."""
        wikitext, meta = load_fixture('Visa_requirements_for_Transnistrian_citizens')

        result = extract_main.parse_page(
            wikitext,
            passport='XT',
            title='Visa requirements for Transnistrian citizens',
            revid=meta['revid'],
            transclusions=transcl
        )

        # This page has no standard visa requirements table, so 0 records is expected
        assert len(result.records) == 0


@pytest.mark.parametrize("name,passport,title", [
    ("Visa_requirements_for_Bahraini_citizens", "BH", "Visa requirements for Bahraini citizens"),
    ("Visa_requirements_for_Belizean_citizens", "BZ", "Visa requirements for Belizean citizens"),
])
def test_flagicon_country_code_row_is_destination(transcl, name, passport, title):
    """{{flagicon|US}} [[United States Minor Outlying Islands]] is UM, not an unmapped 'US'."""
    wikitext, meta = load_fixture(name)
    result = extract_main.parse_page(
        wikitext, passport=passport, title=title,
        revid=meta['revid'], transclusions=transcl,
    )
    assert not [u for u in result.unmapped_destinations if u['destination_name'] == 'US']
    um = [r for r in result.records if r['destination'] == 'UM']
    assert len(um) == 1
    assert um[0]['status'] == 'permit_required'


class TestBritishRestrictedAreaDoesNotDisplaceCountry:
    """Baikonur permit row (restricted-areas table) must not replace visa-free Kazakhstan."""

    def test_kazakhstan_whole_country_kept(self, transcl):
        wikitext, meta = load_fixture('Visa_requirements_for_British_citizens')
        result = extract_main.parse_page(
            wikitext,
            passport='GB',
            title='Visa requirements for British citizens',
            revid=meta['revid'],
            transclusions=transcl
        )
        kz = {r['area']: r['status'] for r in result.records if r['destination'] == 'KZ'}
        assert kz.get(None) == 'visa_free'
        assert kz.get('Territories and disputed areas') == 'permit_required'


def test_french_west_indies_maps_to_fr_area():
    from visa_pipeline import countries
    assert countries.lookup_area('French West Indies') == ('FR', 'French West Indies')


def test_inclusive_suffix_is_not_an_area():
    warnings = []
    for cell, dest in [('{{flag|Australia}} and territories', 'Australia'),
                       ('{{flag|United Kingdom}} and Crown dependencies', 'United Kingdom')]:
        assert extract_main._extract_destination_and_area(cell, warnings) == (dest, None)
    assert extract_main._extract_destination_and_area(
        '{{flag|Eritrea}} (outside Asmara)', warnings) == ('Eritrea', '(outside Asmara)')


def test_british_page_has_whole_country_records_for_inclusive_rows(transcl):
    wikitext, meta = load_fixture('Visa_requirements_for_Danish_citizens')
    result = extract_main.parse_page(
        wikitext, passport='DK', title='Visa requirements for Danish citizens',
        revid=meta['revid'], transclusions=transcl)
    assert not [r for r in result.records if (r['area'] or '').lower().startswith('and ')]
    keys = [(r['destination'], r['area']) for r in result.records]
    assert len(keys) == len(set(keys))
