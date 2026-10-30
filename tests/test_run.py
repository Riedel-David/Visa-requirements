"""Tests for main pipeline run."""

from pathlib import Path

from visa_pipeline.run import needs_update


def test_needs_update_force():
    """Test needs_update with force flag."""
    assert needs_update("DE", 123, {}, Path("."), force=True)


def test_needs_update_missing_output():
    """Test needs_update when output file missing."""
    tmp = Path("/tmp/nonexistent")
    assert needs_update("DE", 123, {}, tmp, force=False)


def test_needs_update_revid_changed():
    """Test needs_update when revid changed."""
    stored = {"DE": {"revid": 122, "timestamp": "2024-01-01T00:00:00Z"}}
    assert needs_update("DE", 123, stored, Path("."), force=False)


def test_needs_update_unchanged(tmp_path):
    """Test needs_update when unchanged."""
    # Create output file
    output_dir = tmp_path / "passports"
    output_dir.mkdir()
    (output_dir / "DE.json").write_text("{}")

    stored = {"DE": {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}}
    assert not needs_update("DE", 123, stored, tmp_path, force=False)
