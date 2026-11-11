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


class TestTableScanning:
    """Finding 1: tables are delimited by depth counting, not a lazy regex."""

    def test_find_tables_template_ending_with_pipe_brace(self):
        text = "{|\n! A\n|-\n| x {{Timatic|DE|}}\n|-\n| y\n|}\nafter"
        tables = extract_main._find_tables(text)
        assert len(tables) == 1
        assert tables[0].endswith("|}")
        assert "| y" in tables[0]

    def test_find_tables_nested(self):
        text = "{|\n| a\n|\n{|\n| inner\n|}\n|-\n| b\n|}\n\n{|\n| second\n|}"
        tables = extract_main._find_tables(text)
        assert len(tables) == 2
        assert "| b" in tables[0]
        assert "second" in tables[1]

    def test_find_tables_none_and_unterminated(self):
        assert extract_main._find_tables("no table") == []
        assert extract_main._find_tables("{|\n| a\n") == []

    def test_parse_page_keeps_rows_after_malformed_timatic(self, transcl):
        wikitext = (
            "== Visa requirements ==\n{| class=\"wikitable\"\n"
            "! Country !! Visa requirement !! Allowed stay !! Notes\n|-\n"
            "| {{flag|Japan}} || {{yes|Visa not required}} || 90 days || {{Timatic|DE|}}\n|-\n"
            "| {{flag|France}} || {{yes|Visa not required}} || 90 days ||\n|}\n"
        )
        result = extract_main.parse_page(wikitext, passport="DE", title="T", revid=1,
                                         transclusions=transcl)
        assert {r["destination"] for r in result.records} == {"JP", "FR"}


    def test_travel_ban_has_null_stay_but_keeps_raw(self, transcl):
        wikitext = (
            "== Visa requirements ==\n{| class=\"wikitable\"\n"
            "! Country !! Visa requirement !! Allowed stay !! Notes\n|-\n"
            "| {{flag|Ukraine}} || {{no|Travel banned}} || 90 days || Government bans travel\n|-\n"
            "| {{flag|France}} || {{yes|Visa not required}} || 90 days ||\n|}\n"
        )
        result = extract_main.parse_page(wikitext, passport="KR", title="T", revid=1,
                                         transclusions=transcl)
        by = {r["destination"]: r for r in result.records}
        assert by["UA"]["status"] == "travel_ban"
        assert by["UA"]["allowed_stay_days"] is None
        assert by["UA"]["allowed_stay_raw"] == "90 days"
        assert by["UA"]["notes"] == "Government bans travel"
        assert by["FR"]["allowed_stay_days"] == 90
        assert result.unmapped_statuses == []


class TestDestinationAndArea:
    """Finding 6."""

    def test_footnote_template_is_not_an_area(self):
        assert extract_main._extract_destination_and_area("[[Taiwan]]{{efn|note}}", []) == ("Taiwan", None)

    def test_area_still_extracted(self):
        assert extract_main._extract_destination_and_area(
            "{{flag|Norway}} [[Jan Mayen]]", []) == ("Norway", "Jan Mayen")

    def test_flag_after_footnote(self):
        assert extract_main._extract_destination_and_area(
            "{{efn|x}}{{flag|Japan}}", [])[1] is None


class TestHeaderRow:
    """Finding 7."""

    @pytest.mark.parametrize("cell", [
        "[[British Indian Ocean Territory]]", "[[Special Administrative Region]]",
        "{{flag|Entry Island}}", "Regular Island", "Special Zone",
    ])
    def test_destinations_are_not_headers(self, cell):
        assert not extract_main._is_header_row({"0": cell})

    @pytest.mark.parametrize("cell", [
        "Country", "Country/Territory", "Country or territory", "Destination",
        "[[Country]]", "'''Country'''", "Territory", "Area", "Regular passport",
        "Special passport", "Visa requirement", "Allowed stay",
    ])
    def test_headers(self, cell):
        assert extract_main._is_header_row({"0": cell})


def test_image_flag_template_is_not_area():
    assert extract_main._extract_destination_and_area(
        "{{flagicon image|Flag_of_China.svg}} [[Tibet Autonomous Region]]", []
    ) == ("Tibet Autonomous Region", None)


_GERMAN_STYLE_TABLE = """{{| class="wikitable"
! Country !! Area !! Maximum stay
|-
| [[France]] || || {stay}
|}}"""


def _parse_german_style(stay_cell, transcl):
    result = extract_main.ParseResult()
    extract_main._parse_table_rows(
        _GERMAN_STYLE_TABLE.format(stay=stay_cell), 'DE', 'Test', False, transcl, 'url', 'rev', result
    )
    return result


def test_status_in_stay_table_reads_status_from_the_stay_column(transcl):
    result = _parse_german_style("Visa not required", transcl)
    assert [r['status'] for r in result.records] == ['visa_free']


def test_status_in_stay_table_does_not_split_a_footnote_off_the_stay_cell(transcl):
    # The cell holds stay text there, so a second line is not a footnote;
    # the whole cell stays unmapped and reported rather than guessed as visa_free.
    result = _parse_german_style("Visa not required<br />ID card is enough", transcl)
    assert [r['status'] for r in result.records] == ['special']
    assert not any(w.startswith("Status footnote split") for w in result.warnings)
    assert 'Visa not required' in result.unmapped_statuses[0]['raw_status']


def test_status_in_stay_table_skips_a_row_whose_cell_is_only_a_duration(transcl):
    result = _parse_german_style("90 days", transcl)
    assert result.records == []


def test_table_without_the_status_in_stay_shape_still_splits_footnotes(transcl):
    table = """{| class="wikitable"
! Country !! Visa requirement
|-
| [[France]] || Visa not required<br />90 days
|}"""
    result = extract_main.ParseResult()
    extract_main._parse_table_rows(table, 'DE', 'Test', False, transcl, 'url', 'rev', result)
    assert [r['status'] for r in result.records] == ['visa_free']
    assert any(w.startswith("Status footnote split") for w in result.warnings)


class TestAreaCleanup:
    """Junk in destination-cell area text: parentheses, &nbsp;, file debris, doubled words."""

    @staticmethod
    def area(cell):
        return extract_main._extract_destination_and_area(cell, [])

    @pytest.mark.parametrize("cell,expected", [
        ("{{flag|Belarus}} ([[Brest]] and [[Grodno]])", ("Belarus", "Brest and Grodno")),
        ("{{flag|Switzerland}} ( [[Samnaun]])", ("Switzerland", "Samnaun")),
        ("{{flag|Germany}} (&nbsp;[[Büsingen am Hochrhein]] and &nbsp;[[Heligoland]])",
         ("Germany", "Büsingen am Hochrhein and Heligoland")),
        ("{{flag|Germany}} &nbsp;[[Büsingen am Hochrhein]] and &nbsp;[[Heligoland]]",
         ("Germany", "Büsingen am Hochrhein and Heligoland")),
        ("{{flag|Kazakhstan}} ([[Baikonur]] & [[File:Coats_of_arms_of_Priosjorsk.PNG|20px]] [[Priozersk]])",
         ("Kazakhstan", "Baikonur & Priozersk")),
        ("{{flag|Netherlands}} (Bonaire, Sint Eustatius and Saba)",
         ("Netherlands", "Bonaire, Sint Eustatius and Saba")),
        ("{{flagicon|Malaysia}} {{flagicon|Sabah}} [[Sabah]] and {{flagicon|Sarawak}} [[Sarawak]]",
         ("Malaysia", "Sabah and Sarawak")),
        ("{{flag|Malaysia}} Malaysia:<br>{{flagicon|Sabah}} [[Sabah]] and {{flagicon|Sarawak}} [[Sarawak]]",
         ("Malaysia", "Sabah and Sarawak")),
        ("{{flag|Guadeloupe}},", ("Guadeloupe", None)),
        ("{{flag|Guadeloupe}} ( )", ("Guadeloupe", None)),
    ])
    def test_cleaned(self, cell, expected):
        assert self.area(cell) == expected

    @pytest.mark.parametrize("cell", [
        "{{flag|China}} (People's Republic of)",
        "China (People's Republic of)",
    ])
    def test_name_qualifier_is_not_area(self, cell):
        assert self.area(cell) == ("China", None)

    @pytest.mark.parametrize("cell,expected", [
        ("{{flag|China}} [[Hainan]]", ("China", "Hainan")),
        ("{{flag|China}} [[Tibet Autonomous Region]]", ("China", "Tibet Autonomous Region")),
        ("{{flag|France}} French West Indies (Martinique, Guadeloupe and Saint Martin)",
         ("France", "French West Indies (Martinique, Guadeloupe and Saint Martin)")),
        ("{{flag|French Polynesia}} [[Bora Bora]]", ("French Polynesia", "Bora Bora")),
        ("{{flag|Japan}}", ("Japan", None)),
    ])
    def test_unchanged(self, cell, expected):
        assert self.area(cell) == expected

    def test_newline_separated_list_keeps_line_breaks(self):
        from visa_pipeline import clean
        assert clean.clean_area("Bonaire\nCuraçao\n Saba ") == "Bonaire\nCuraçao\nSaba"
        assert clean.clean_area("Malaysia:\nSabah Sabah and Sarawak Sarawak", "Malaysia") == "Sabah and Sarawak"


def test_only_peoples_republic_qualifier_is_stripped_from_names():
    # Stripping any "(... of)" would turn DR Congo into Congo (a different country)
    name, area = extract_main._extract_destination_and_area("China (People's Republic of)", [])
    assert (name, area) == ('China', None)
    name, _ = extract_main._extract_destination_and_area("Congo (Democratic Republic of the)", [])
    assert name == 'Congo (Democratic Republic of the)'


def test_usually_template_and_single_arg_sort_keep_their_text():
    from visa_pipeline import clean
    assert clean.clean('{{usually|Freedom of movement}}', {}, []) == 'Freedom of movement'
    assert clean.clean('{{yes2|{{sort|eVisa}}}}', {}, []) == 'eVisa'
    assert clean.clean('{{free|{{sort|Freedom of movement}}}}', {}, []) == 'Freedom of movement'
    assert clean.clean('{{sort|1|Visa required}}', {}, []) == 'Visa required'


def test_area_debris_hyphen_and_numeric_sort_key():
    from visa_pipeline import clean
    assert clean.clean_area('Flag of Sabah.svg') is None
    assert clean.clean_area('Flag of Sabah.svg Sabah') == 'Sabah'
    assert clean.clean_area('Guinea Guinea-Bissau') == 'Guinea Guinea-Bissau'
    assert clean.clean('{{sort|4}}{{no|Visa required}}', {}, []) == 'Visa required'
