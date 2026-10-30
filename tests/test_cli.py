"""Tests for the CLI entry point."""

import sys

import pytest

from visa_pipeline import __main__ as cli


@pytest.mark.parametrize("argv", [
    ["run", "--only", "DE,us", "--force"],
    ["--only", "DE,us", "--force"],
])
def test_cli_accepts_optional_run_command(monkeypatch, argv):
    calls = []
    monkeypatch.setattr(cli, "run", lambda **kw: calls.append(kw) or 0)
    monkeypatch.setattr(sys, "argv", ["visa_pipeline", *argv])

    assert cli.main() == 0
    assert calls[0]["only"] == ["DE", "US"]
    assert calls[0]["force"] is True


def test_cli_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["visa_pipeline", "publish"])
    with pytest.raises(SystemExit):
        cli.main()
