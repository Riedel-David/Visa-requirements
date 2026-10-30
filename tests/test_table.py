"""Tests for table.py - wikitable parsing."""

from visa_pipeline import table


class TestBasicTable:
    """Tests for basic table parsing."""

    def test_simple_table(self):
        """Test a simple 2x2 table."""
        wiki_table = """
{| class="wikitable"
|-
! Header 1
! Header 2
|-
| Cell 1
| Cell 2
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        assert rows[0] == {"0": "Header 1", "1": "Header 2"}
        assert rows[1] == {"0": "Cell 1", "1": "Cell 2"}

    def test_inline_cells(self):
        """Test inline cells with || separator."""
        wiki_table = """
{| class="wikitable"
|-
! Header 1 !! Header 2 !! Header 3
|-
| Cell 1 || Cell 2 || Cell 3
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        assert rows[1] == {"0": "Cell 1", "1": "Cell 2", "2": "Cell 3"}


class TestCellAttributes:
    """Tests for cell attributes."""

    def test_colspan(self):
        """Test colspan attribute."""
        wiki_table = """
{| class="wikitable"
|-
! colspan="2" | Wide Header
|-
| Cell 1 || Cell 2
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        # Wide header should span both columns
        assert rows[0]["0"] == "Wide Header"
        assert rows[0]["1"] == "Wide Header"

    def test_glued_attribute(self):
        """Test glued attribute without pipe separator."""
        wiki_table = """
{| class="wikitable"
|-
! Header
|-
| data-sort-value="4" {{no|Visa required}}
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        # Should extract content after the attribute
        assert "{{no|Visa required}}" in rows[1]["0"]


class TestGroupHeaders:
    """Tests for group header rows."""

    def test_group_header(self):
        """Test full-width group header with large colspan."""
        wiki_table = """
{| class="wikitable"
|-
! colspan="4" | Europe
|-
| Country 1 || Status 1 || Stay 1 || Notes 1
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        # First row should be a group label
        assert "_group_label" in rows[0]
        assert rows[0]["_group_label"] == "Europe"


class TestNestedTemplates:
    """Tests for nested templates and links."""

    def test_pipe_in_template(self):
        """Test that pipes inside {{ }} are not treated as cell separators."""
        wiki_table = """
{| class="wikitable"
|-
! Header 1 || Header 2
|-
| {{flag|United States}} || {{yes|Visa not required}}
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        # Should have exactly 2 cells in data row
        assert "0" in rows[1]
        assert "1" in rows[1]
        assert "{{flag|United States}}" in rows[1]["0"]
        assert "{{yes|Visa not required}}" in rows[1]["1"]

    def test_pipe_in_link(self):
        """Test that pipes inside [[ ]] are not treated as cell separators."""
        wiki_table = """
{| class="wikitable"
|-
! Header 1 || Header 2
|-
| [[United States|USA]] || [[Visa|Entry permit]]
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        assert "[[United States|USA]]" in rows[1]["0"]
        assert "[[Visa|Entry permit]]" in rows[1]["1"]


class TestMultilineCells:
    """Tests for multi-line cell content."""

    def test_multiline(self):
        """Test cells spanning multiple lines."""
        wiki_table = """
{| class="wikitable"
|-
! Header 1
! Header 2
|-
| Line 1
Line 2
Line 3
| Single line
|}
"""
        rows = table.parse_table(wiki_table)
        assert len(rows) == 2
        # First cell should contain newlines
        assert "\n" in rows[1]["0"]
        assert "Line 1" in rows[1]["0"]
        assert "Line 3" in rows[1]["0"]
