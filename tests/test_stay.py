"""Tests for stay.py - stay duration parsing."""

from visa_pipeline import stay


class TestSimpleDurations:
    """Tests for simple duration formats."""

    def test_days(self):
        assert stay.parse_stay("90 days") == (90, None)
        assert stay.parse_stay("30 days") == (30, None)
        assert stay.parse_stay("1 day") == (1, None)
        assert stay.parse_stay("180 days") == (180, None)

    def test_months(self):
        assert stay.parse_stay("3 months") == (90, None)
        assert stay.parse_stay("6 months") == (180, None)
        assert stay.parse_stay("1 month") == (30, None)
        assert stay.parse_stay("12 months") == (365, None)

    def test_years(self):
        assert stay.parse_stay("1 year") == (365, None)
        assert stay.parse_stay("2 years") == (730, None)

    def test_empty(self):
        assert stay.parse_stay("") == (None, None)
        assert stay.parse_stay("   ") == (None, None)


class TestComplexDurations:
    """Tests for complex duration formats with context."""

    def test_within_period(self):
        days, note = stay.parse_stay("30 days within 180")
        assert days == 30
        assert "within 180" in note

    def test_in_any_period(self):
        days, note = stay.parse_stay("90 days in any 180-day period")
        assert days == 90
        assert note is not None

    def test_unlimited(self):
        days, note = stay.parse_stay("Unlimited")
        assert days is None
        assert note == "Unlimited"

    def test_freedom_of_movement(self):
        days, note = stay.parse_stay("Freedom of movement")
        assert days is None
        assert note == "Freedom of movement"

    def test_indefinite(self):
        days, note = stay.parse_stay("Indefinite")
        assert days is None
        assert note == "Indefinite"


class TestAmbiguousDurations:
    """Tests for ambiguous or ranged durations."""

    def test_range(self):
        days, note = stay.parse_stay("14–30 days")
        assert days is None
        assert note == "14–30 days"

    def test_range_with_dash(self):
        days, note = stay.parse_stay("30-90 days")
        assert days is None
        assert note == "30-90 days"

    def test_multiple_options(self):
        days, note = stay.parse_stay("30 days or 90 days")
        assert days is None
        assert "or" in note

    def test_complex_text(self):
        days, note = stay.parse_stay("Up to 90 days, depending on purpose")
        # Should extract 90 days
        assert days == 90
        # Should include extra context
        assert note is not None
