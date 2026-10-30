"""Tests for status.py - visa status text mapping."""

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


class TestNormalization:
    """Tests for status text normalization."""

    def test_case_insensitive(self):
        assert status.parse_status("VISA REQUIRED") == ("visa_required", [])
        assert status.parse_status("Visa Required") == ("visa_required", [])
        assert status.parse_status("visa required") == ("visa_required", [])

    def test_whitespace_normalization(self):
        assert status.parse_status("Visa  \t  required") == ("visa_required", [])
        assert status.parse_status("  Visa required  ") == ("visa_required", [])
