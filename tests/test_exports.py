"""Tests for CSV exports."""

import csv
import json
from pathlib import Path

import pytest

from visa_pipeline import exports
from visa_pipeline.exports import load_iso3_table, to_iso3, write_csv_exports

MAIN_PASSPORTS = Path(__file__).resolve().parents[1] / "data" / "passports"


def rec(p, d, status, area=None):
    return {"passport": p, "destination": d, "area": area, "status": status}


DATA = {
    "US": [rec("US", "JP", "visa_free"), rec("US", "XK", "evisa"), rec("US", "JP", "special", area="Okinawa")],
    "DE": [rec("DE", "JP", "visa_free"), rec("DE", "FR", "visa_free"), rec("DE", "JP", "evisa")],
}


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_outputs(tmp_path):
    write_csv_exports(tmp_path, DATA)
    assert read(tmp_path / exports.TIDY_ISO2) == [
        ["Passport", "Destination", "Requirement"],
        ["DE", "FR", "visa_free"],
        ["DE", "JP", "visa_free"],  # first whole-country record wins
        ["US", "JP", "visa_free"],  # area rows ignored
        ["US", "XK", "evisa"],
    ]
    assert read(tmp_path / exports.TIDY_ISO3)[1:] == [
        ["DEU", "FRA", "visa_free"],
        ["DEU", "JPN", "visa_free"],
        ["USA", "JPN", "visa_free"],
        ["USA", "XKX", "evisa"],
    ]
    assert read(tmp_path / exports.MATRIX_ISO2) == [
        ["Passport", "FR", "JP", "XK"],
        ["DE", "visa_free", "visa_free", ""],
        ["US", "", "visa_free", "evisa"],
    ]


def test_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    write_csv_exports(a, DATA)
    write_csv_exports(b, {k: DATA[k] for k in reversed(list(DATA))})
    for name in (exports.TIDY_ISO2, exports.TIDY_ISO3, exports.MATRIX_ISO2):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_iso3_mapping():
    assert to_iso3("DE") == "DEU"
    assert to_iso3("XK") == "XKX"
    for x in ("XN", "XS", "XA", "XO", "XT", "XW"):
        assert to_iso3(x) == x


def test_missing_code_raises(tmp_path):
    with pytest.raises(KeyError):
        to_iso3("ZZ")
    with pytest.raises(KeyError):
        write_csv_exports(tmp_path, {"ZZ": [rec("ZZ", "DE", "visa_free")]})


def test_missing_table_fails_loudly(monkeypatch):
    class Missing:
        def joinpath(self, name):
            return Path("/nonexistent") / name

    monkeypatch.setattr(exports.resources, "files", lambda pkg: Missing())
    load_iso3_table.cache_clear()
    try:
        with pytest.raises(FileNotFoundError):
            load_iso3_table()
    finally:
        load_iso3_table.cache_clear()


@pytest.mark.skipif(not MAIN_PASSPORTS.is_dir(), reason="main checkout data not available")
def test_all_real_codes_resolve():
    codes = set()
    for f in MAIN_PASSPORTS.glob("*.json"):
        for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
            codes.add(r["passport"])
            codes.add(r["destination"])
    assert codes
    for c in codes:
        to_iso3(c)
