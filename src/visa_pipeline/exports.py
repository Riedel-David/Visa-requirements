"""CSV exports derived from the per-passport records (same source as all.json)."""

import csv
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

TIDY_ISO2 = "passport-index-tidy-iso2.csv"
TIDY_ISO3 = "passport-index-tidy-iso3.csv"
MATRIX_ISO2 = "passport-index-matrix-iso2.csv"


@lru_cache(maxsize=1)
def load_iso3_table() -> dict[str, str]:
    """Load the ISO 3166-1 alpha-2 -> alpha-3 table; raises if the file is missing."""
    text = resources.files("visa_pipeline").joinpath("iso3.json").read_text(encoding="utf-8")
    return json.loads(text)


def to_iso3(code: str) -> str:
    """Convert an alpha-2 code to alpha-3. Unknown codes raise KeyError."""
    table = load_iso3_table()
    if code not in table:
        raise KeyError(f"No ISO-3 code for {code!r}")
    return table[code]


def collect_statuses(all_passports_data: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], str]:
    """Whole-country (area is null) status per (passport, destination).

    If a pair has several whole-country records, the first one in record order wins.
    """
    result: dict[tuple[str, str], str] = {}
    for passport, records in all_passports_data.items():
        for r in records:
            if r.get("area") is not None:
                continue
            result.setdefault((passport, r["destination"]), r["status"])
    return result


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def write_csv_exports(data_dir: Path, all_passports_data: dict[str, list[dict[str, Any]]]) -> None:
    """Write the three CSV files into data_dir. Output is sorted and deterministic."""
    statuses = collect_statuses(all_passports_data)
    pairs = sorted(statuses)
    header = ["Passport", "Destination", "Requirement"]

    # Build everything first so a failing ISO-3 lookup leaves no partial output.
    tidy2 = [header] + [[p, d, statuses[(p, d)]] for p, d in pairs]
    tidy3 = [header] + [[to_iso3(p), to_iso3(d), statuses[(p, d)]] for p, d in pairs]
    passports = sorted({p for p, _ in pairs})
    destinations = sorted({d for _, d in pairs})
    matrix = [["Passport"] + destinations] + [
        [p] + [statuses.get((p, d), "") for d in destinations] for p in passports
    ]

    _write_csv(data_dir / TIDY_ISO2, tidy2)
    _write_csv(data_dir / TIDY_ISO3, tidy3)
    _write_csv(data_dir / MATRIX_ISO2, matrix)
