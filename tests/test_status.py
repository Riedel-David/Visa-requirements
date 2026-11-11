"""Tests for status.py - visa status text mapping."""

import pytest

from visa_pipeline import status


class TestSingleStatus:
    """Tests for single status values."""

    def test_visa_free(self):
        assert status.parse_status("Visa not required") == ("visa_free", [])
        assert status.parse_status("Freedom of movement") == ("visa_free", [])
        assert status.parse_status("Visa-free") == ("visa_free", [])

    def test_eta(self):
        assert status.parse_status("Electronic Travel Authorisation") == ("eta", [])
        assert status.parse_status("ETA") == ("eta", [])
        assert status.parse_status("ESTA") == ("eta", [])
        assert status.parse_status("eVisitor") == ("eta", [])

    def test_evisa(self):
        assert status.parse_status("eVisa") == ("evisa", [])
        assert status.parse_status("e-Visa") == ("evisa", [])
        assert status.parse_status("Online visa") == ("evisa", [])

    def test_visa_on_arrival(self):
        assert status.parse_status("Visa on arrival") == ("visa_on_arrival", [])
        assert status.parse_status("Free visa on arrival") == ("visa_on_arrival", [])
        assert status.parse_status("e-VOA") == ("visa_on_arrival", [])

    def test_visa_required(self):
        assert status.parse_status("Visa required") == ("visa_required", [])
        assert status.parse_status("Online visa required") == ("visa_required", [])

    def test_permit_required(self):
        assert status.parse_status("Special permit required") == ("permit_required", [])
        assert status.parse_status("Permit required") == ("permit_required", [])
        assert status.parse_status("TTP required") == ("permit_required", [])

    def test_admission_refused(self):
        assert status.parse_status("Admission refused") == ("admission_refused", [])
        assert status.parse_status("Entry denied") == ("admission_refused", [])

    def test_travel_ban(self):
        for text in ("Travel banned", "travel prohibited", "  Travel   Banned.", "TRAVEL PROHIBITED"):
            assert status.parse_status(text) == ("travel_ban", [])

    def test_travel_ban_neighbours_unchanged(self):
        assert status.parse_status("Travel not permitted") == ("admission_refused", [])
        assert status.parse_status("Travel restricted") == ("special", [])
        assert status.parse_status("Visa issuance suspended") == ("special", [])

    def test_travel_ban_in_combined_cell_wins(self):
        # The home government's ban overrides the destination's own regime
        assert status.parse_status("eVisa\nTravel banned") == ("travel_ban", ["evisa"])
        assert status.parse_status("Visa not required\nTravel banned") == ("travel_ban", ["visa_free"])
        assert status.parse_status("Travel prohibited or Visa required") == ("travel_ban", ["visa_required"])

    def test_travel_ban_with_unmapped_part_is_special(self):
        assert status.parse_status("Something unknown\nTravel banned") == ("special", [])

    def test_unmapped(self):
        primary, alts = status.parse_status("Something completely unknown")
        assert primary == "special"
        assert alts == []


class TestCombinedStatus:
    """Tests for combined status values like 'eVisa / Visa on arrival'."""

    def test_evisa_or_voa(self):
        primary, alts = status.parse_status("eVisa / Visa on arrival")
        assert primary == "visa_on_arrival"
        assert "evisa" in alts

    def test_eta_or_visa_free(self):
        primary, alts = status.parse_status("ETA or Visa not required")
        assert primary == "visa_free"
        assert "eta" in alts

    def test_multiple_with_or(self):
        primary, alts = status.parse_status("eVisa or Visa on arrival")
        assert primary == "visa_on_arrival"
        assert "evisa" in alts

    def test_alternatives_keep_order_of_appearance(self):
        primary, alts = status.parse_status("Visa required / eVisa / Visa not required")
        assert primary == "visa_free"
        assert alts == ["visa_required", "evisa"]

    def test_unmapped_part_makes_whole_cell_special(self):
        assert status.parse_status("Visa on arrival / Frobnicate") == ("special", [])

    def test_slash_with_various_spacing(self):
        # Test "ETA/ Visa on arrival", "ETA /Visa on arrival", "ETA/Visa on arrival"
        assert status.parse_status("ETA/ Visa on arrival") == ("visa_on_arrival", ["eta"])
        assert status.parse_status("ETA /Visa on arrival") == ("visa_on_arrival", ["eta"])
        assert status.parse_status("ETA/Visa on arrival") == ("visa_on_arrival", ["eta"])

    def test_newline_separator(self):
        # Test "Visa not required\neVisa" -> ('visa_free', ['evisa'])
        assert status.parse_status("Visa not required\neVisa") == ("visa_free", ["evisa"])

    def test_combined_with_special(self):
        # An unmapped part still makes the whole cell special
        assert status.parse_status("eVisa\nSomething unknown") == ("special", [])


class TestNormalization:
    """Tests for status text normalization."""

    def test_case_insensitive(self):
        assert status.parse_status("VISA REQUIRED") == ("visa_required", [])
        assert status.parse_status("Visa Required") == ("visa_required", [])
        assert status.parse_status("visa required") == ("visa_required", [])

    def test_whitespace_normalization(self):
        assert status.parse_status("Visa  \t  required") == ("visa_required", [])
        assert status.parse_status("  Visa required  ") == ("visa_required", [])

    def test_curly_apostrophe_normalization(self):
        # Test curly apostrophes are normalized to straight apostrophes
        assert status.parse_status("Visitor's permit on arrival") == ("visa_on_arrival", [])
        assert status.parse_status("Visitor's permit on arrival") == ("visa_on_arrival", [])

    def test_trailing_period_stripping(self):
        assert status.parse_status("Visa required.") == ("visa_required", [])
        assert status.parse_status("Visa not required.") == ("visa_free", [])


class TestFreePrefixInCombined:
    def test_free_eta_or_voa(self):
        assert status.parse_status("Free ETA / Visa on arrival") == ('visa_on_arrival', ['eta'])

    def test_free_prefix_other_part(self):
        assert status.parse_status("Visa on arrival / Free eVisa") == ('visa_on_arrival', ['evisa'])

    def test_free_unmapped_remainder_is_special(self):
        assert status.parse_status("Free foo / Visa on arrival") == ('special', [])


def test_tourist_card_and_typo_variants_are_mapped():
    assert status.parse_status('Tourist card required') == ('visa_required', [])
    assert status.parse_status('eVisa/Tourist Card required') == ('evisa', ['visa_required'])
    assert status.parse_status('Tourist card') == ('evisa', [])  # decided: bare Tourist card is evisa
    assert status.parse_status('Vesa required') == ('visa_required', [])
    assert status.parse_status('Visa is required') == ('visa_required', [])
    assert status.parse_status('Tourist Cards on arrival') == ('visa_on_arrival', [])
    assert status.parse_status('Free Visa stamp on arrival') == ('visa_on_arrival', [])


@pytest.mark.parametrize("text,expected", [
    ("Required", "visa_required"),
    ("Pre-enrolment", "evisa"),
    ("Tourist Card", "evisa"),
    ("Tourist Card / eVisa", "evisa"),
    ("Free electronic travel authorisation", "eta"),
    ("Free electronic travel authorization", "eta"),
    ("eVisitors", "eta"),
    ("Special entry permit", "eta"),
])
def test_new_keys(text, expected):
    assert status.parse_status(text)[0] == expected


@pytest.mark.parametrize("text", ["Visa not", "90 days; ID card valid."])
def test_unmapped_text_stays_special_and_reported(text):
    """Not in STATUS_MAP on purpose: stays special and stays reported as unmapped."""
    assert status.parse_status(text) == ("special", [])


@pytest.mark.parametrize("text", ["Unknown", "Admission restricted"])
def test_deliberate_special_mappings(text):
    """In STATUS_MAP as 'special' so they show in the report with context."""
    assert status.STATUS_MAP[status.normalize_status(text)] == "special"
    assert status.parse_status(text) == ("special", [])


class TestSplitFootnote:
    def test_footnote_after_status(self):
        text = "Visa not required\nValid ID card is enough"
        assert status.split_footnote(text) == ("Visa not required", "Valid ID card is enough")

    def test_combined_status_with_footnote_splits(self):
        text = "eVisa / Visa on arrival\nNote text"
        assert status.split_footnote(text) == ("eVisa / Visa on arrival", "Note text")

    def test_later_alternative_line_leaves_text_unchanged(self):
        text = "Visa not required\nsee note\neVisa"
        assert status.split_footnote(text) == (text, None)

    def test_bullets_stripped_and_joined(self):
        text = "Visa not required\n* first\n\u2022 second"
        assert status.split_footnote(text) == ("Visa not required", "first second")

    def test_combined_status_untouched(self):
        assert status.split_footnote("Visa not required\neVisa") == ("Visa not required\neVisa", None)

    def test_unmapped_first_line_untouched(self):
        assert status.split_footnote("Whatever\nmore") == ("Whatever\nmore", None)

    def test_single_line_untouched(self):
        assert status.split_footnote("Visa not required") == ("Visa not required", None)

    @pytest.mark.parametrize("text", [
        "Visa required\nVisa on arrival at airport",
        "Visa not required\nsee note / eVisa",
        "Visa not required\nsee note\nRequired",
        "Visa not required\nAn ETA may apply",
    ])
    def test_embedded_alternative_leaves_text_unchanged(self, text):
        assert status.split_footnote(text) == (text, None)

    def test_short_key_needs_word_boundary(self):
        text = "Visa not required\nComplete the form quietly"
        assert status.split_footnote(text) == ("Visa not required", "Complete the form quietly")

    def test_leading_blank_line(self):
        text = "\nVisa not required\nnote"
        assert status.split_footnote(text) == (text, None)

    def test_bare_bullet_line_is_not_a_footnote(self):
        assert status.split_footnote("Visa not required\n*") == ("Visa not required\n*", None)

    def test_empty_bullets_dropped_single_space(self):
        text = "Visa not required\n* a\n*\n* b"
        assert status.split_footnote(text) == ("Visa not required", "a b")

    def test_same_status_phrase_in_footnote_splits(self):
        # "id card" maps to visa_free, the first line's status; line alone is special
        assert status.split_footnote("Visa not required\nid card is enough") == (
            "Visa not required", "id card is enough")

    def test_different_status_phrase_in_footnote_blocks_split(self):
        # "e-tourist card" maps to evisa; the line as a whole is not a status
        text = "Visa not required\nan e-tourist card helps"
        assert status.split_footnote(text) == (text, None)

    def test_trailing_newline_is_unchanged(self):
        assert status.split_footnote("Visa not required\n") == ("Visa not required\n", None)


class TestSplitFootnoteStaysConservative:
    """A footnote that mentions "required" or "unknown" is NOT split off, on purpose.

    Splitting it would record the first line's status (e.g. visa_free) for a cell whose
    footnote may carry a real condition ("Permits required for restricted areas") or an
    admitted uncertainty ("Status unknown"). Left whole, the cell becomes `special` and is
    reported for review, which is the safe outcome.
    """

    @pytest.mark.parametrize("footnote", [
        "Permits required for restricted areas",
        "Passport required",
        "Status unknown",
        "Duration unknown",
    ])
    def test_footnote_with_required_or_unknown_keeps_the_cell_whole(self, footnote):
        text = f"Visa not required\n{footnote}"
        assert status.split_footnote(text) == (text, None)

    def test_cell_that_really_says_visa_required_still_parses_as_visa_required(self):
        assert status.split_footnote("Visa required") == ("Visa required", None)
        assert status.parse_status("Visa required") == ("visa_required", [])
