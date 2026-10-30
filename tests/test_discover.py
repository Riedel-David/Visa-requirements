"""Tests for page discovery."""

from unittest.mock import MagicMock

import pytest

from visa_pipeline.discover import discover_pages


def test_discover_pages_basic():
    """Test basic page discovery."""
    client = MagicMock()
    # Use side_effect to return specific values for specific calls
    client.category_members.side_effect = [
        # First call: main category, articles (namespace=0)
        ["Visa requirements for German citizens", "Visa requirements for French citizens"],
        # Second call: main category, subcategories (namespace=14)
        []  # No subcategories
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 2
    assert pages[0]["passport"] == "FR"  # Sorted alphabetically
    assert pages[1]["passport"] == "DE"


def test_discover_pages_unmapped_demonym():
    """Test unmapped demonym."""
    client = MagicMock()
    client.category_members.side_effect = [
        ["Visa requirements for Atlantean citizens"],
        []
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 1
    assert pages[0]["passport"] is None
    assert "unmapped demonym" in pages[0]["reason"]


def test_discover_pages_wrong_pattern():
    """Test title not matching pattern."""
    client = MagicMock()
    client.category_members.side_effect = [
        ["Visa policy of Germany"],
        []
    ]

    pages = discover_pages(client, {})

    assert len(pages) == 1
    assert pages[0]["passport"] is None
    assert "does not match pattern" in pages[0]["reason"]


def test_discover_pages_with_override():
    """Test override mapping."""
    client = MagicMock()
    client.category_members.side_effect = [
        ["Visa requirements for British citizens"],
        []
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
    client = MagicMock()
    client.category_members.side_effect = [
        ["Visa requirements for British Overseas Territories citizens"],
        []
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
    client = MagicMock()
    client.category_members.side_effect = [
        [
            "Visa requirements for German citizens",
            "Visa requirements for German nationals"  # Would map to same code via override
        ],
        []
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
    client = MagicMock()

    # Configure side_effect to handle all calls in sequence
    client.category_members.side_effect = [
        # First call: main category, articles (namespace=0)
        ["Visa requirements for German citizens"],
        # Second call: main category, subcategories (namespace=14)
        ["Category:Visa requirements by European nationality"],
        # Third call: subcategory, articles (namespace=0)
        ["Visa requirements for French citizens"]
    ]

    pages = discover_pages(client, {})

    # Should find both German and French citizens
    assert len(pages) == 2
    passports = {p["passport"] for p in pages}
    assert passports == {"DE", "FR"}
    # Should call category_members 3 times
    assert client.category_members.call_count == 3


def test_load_overrides_missing_file_raises(tmp_path):
    from visa_pipeline.discover import load_overrides
    with pytest.raises(FileNotFoundError):
        load_overrides(tmp_path / "nope.json")


def test_countries_overrides_missing_file_raises(monkeypatch, tmp_path):
    from visa_pipeline import countries
    monkeypatch.setattr(countries, "_overrides_cache", None)
    monkeypatch.setattr(countries, "files", lambda pkg: tmp_path)
    with pytest.raises(FileNotFoundError):
        countries._load_overrides()
    assert countries._overrides_cache is None


def test_package_data_includes_overrides():
    import tomllib
    from pathlib import Path
    cfg = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    assert "overrides/*.json" in cfg["tool"]["setuptools"]["package-data"]["visa_pipeline"]
