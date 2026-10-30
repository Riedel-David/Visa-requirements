"""Tests for page discovery."""

from unittest.mock import Mock

from visa_pipeline.discover import discover_pages


def test_discover_pages_basic():
    """Test basic page discovery."""
    client = Mock()
    client.category_members.return_value = [
        "Visa requirements for German citizens",
        "Visa requirements for French citizens"
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 2
    assert pages[0]["passport"] == "DE"
    assert pages[1]["passport"] == "FR"


def test_discover_pages_unmapped_demonym():
    """Test unmapped demonym."""
    client = Mock()
    client.category_members.return_value = [
        "Visa requirements for Atlantean citizens"
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 1
    assert pages[0]["passport"] is None
    assert "unmapped demonym" in pages[0]["reason"]


def test_discover_pages_wrong_pattern():
    """Test title not matching pattern."""
    client = Mock()
    client.category_members.return_value = [
        "Visa policy of Germany"
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 1
    assert pages[0]["passport"] is None
    assert "does not match pattern" in pages[0]["reason"]


def test_discover_pages_with_override():
    """Test override mapping."""
    client = Mock()
    client.category_members.return_value = [
        "Visa requirements for British citizens"
    ]

    overrides = {
        "Visa requirements for British citizens": "GB"
    }

    pages = discover_pages(client, overrides)

    assert len(pages) == 1
    assert pages[0]["passport"] == "GB"
    assert pages[0]["reason"] == "override"


def test_discover_pages_excluded_override():
    """Test excluded page (null override)."""
    client = Mock()
    client.category_members.return_value = [
        "Visa requirements for British Overseas Territories citizens"
    ]

    overrides = {
        "Visa requirements for British Overseas Territories citizens": None
    }

    pages = discover_pages(client, overrides)

    assert len(pages) == 1
    assert pages[0]["passport"] is None
    assert pages[0]["reason"] == "excluded by override"


def test_discover_pages_duplicate_detection():
    """Test duplicate passport code detection."""
    client = Mock()
    client.category_members.return_value = [
        "Visa requirements for German citizens",
        "Visa requirements for German nationals"  # Would map to same code
    ]

    overrides = {
        "Visa requirements for German nationals": "DE"
    }

    pages = discover_pages(client, overrides)

    # First should succeed, second should be marked as duplicate
    assert pages[0]["passport"] == "DE"
    assert pages[1]["passport"] is None
    assert "duplicate" in pages[1]["reason"]


def test_discover_pages_with_subcategories():
    """Test discovery with subcategories."""
    client = Mock()

    def category_members(category, namespace=0):
        if namespace == 0:  # Articles
            return ["Visa requirements for German citizens"]
        else:  # Categories
            return ["Category:Visa requirements by European nationality"]

    client.category_members.side_effect = category_members

    discover_pages(client, {})

    # Should call twice: once for namespace 0, once for namespace 14
    assert client.category_members.call_count >= 2
