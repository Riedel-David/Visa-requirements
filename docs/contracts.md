# Internal contracts (binding for all modules)

Package: `src/visa_pipeline/`. Python 3.11+. Tests: `tests/`, fixtures in `tests/fixtures/`.

## Module ownership

| Module | Owner branch | Purpose |
|---|---|---|
| `clean.py`, `table.py`, `status.py`, `stay.py`, `countries.py`, `transclusions.py`, `extract_main.py`, `overrides/destinations.json` | parser | wikitext -> records |
| `api.py`, `discover.py`, `demonyms.py`, `validate.py`, `publish.py`, `run.py`, `__main__.py`, `schema/passport.schema.json`, `overrides/passports.json` | pipeline | fetch, state, safety, output |
| `.github/`, `README.md`, `DATA_FORMAT.md`, `LICENSE`, `LICENSE-DATA.md`, community files | repo-setup | hygiene, workflow, docs |

`overrides/` lives at `src/visa_pipeline/overrides/` (package data).

## Parser API (parser branch provides, pipeline branch calls)

```python
# visa_pipeline/transclusions.py
def parse_template(wikitext: str) -> dict[str, str]:
    """Split 'Template:Transcluded sections for the visa articles' wikitext into
    {section heading: section wikitext}. Used to resolve
    {{#section-h::Template:Transcluded sections for the visa articles|<heading>}}."""

# visa_pipeline/extract_main.py
@dataclass
class ParseResult:
    records: list[dict]               # Record dicts, see below
    unmapped_statuses: list[dict]     # {"passport","destination_name","raw_status"}
    unmapped_destinations: list[dict] # {"passport","destination_name","section"}
    warnings: list[str]

def parse_page(wikitext: str, *, passport: str, title: str, revid: int,
               transclusions: dict[str, str]) -> ParseResult: ...
```

`parse_page` must be pure (no network). Pipeline imports `TEMPLATE_TITLE` from
`transclusions.py` = `"Template:Transcluded sections for the visa articles"`.

## Status enum

`visa_free | visa_on_arrival | eta | evisa | visa_required | permit_required | admission_refused | special`

Order = least to most restrictive (`special` sits outside the order). For combined statuses
("eVisa / Visa on arrival"), `status` is the least restrictive one and the others go in
`alternative_statuses`, in the order they appear. Unmapped text becomes `special` and is
added to `unmapped_statuses`. Never guess.

## Record (one per passport x destination x area)

```json
{
  "passport": "DE",
  "destination": "JP",
  "destination_name": "Japan",
  "area": null,
  "status": "visa_free",
  "alternative_statuses": [],
  "allowed_stay_days": 90,
  "allowed_stay_raw": "90 days",
  "notes": "cleaned plain text, bullets joined with '\n'",
  "is_territory_or_restricted": false,
  "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
  "source_revision": "1379323599"
}
```

- `destination`: ISO 3166-1 alpha-2, or a user-assigned X-code from `overrides/destinations.json`
  (XK Kosovo, XN Northern Cyprus, XS Somaliland, others assigned there). If a name can't be
  mapped, the row is skipped and listed in `unmapped_destinations`.
- `area`: null for whole-country rows. Set for sub-national rows (e.g. "Tibet Autonomous Region",
  "Brest and Grodno"). For those rows, `destination` is the sovereign's code.
- `allowed_stay_days`: int or null. `allowed_stay_raw`: cleaned cell text or null.
- Unique key within a passport: `(destination, area)`. Duplicates: keep the first, add a warning.

## Per-passport file `data/passports/<ISO2>.json`

```json
{
  "schema_version": "1.0.0",
  "passport": "DE",
  "source_title": "Visa requirements for German citizens",
  "source_url": "...",
  "source_revision": "1379323599",
  "source_timestamp": "2026-10-09T12:34:56Z",
  "generated_at": "2026-10-30T06:00:00Z",
  "license": "CC BY-SA 4.0",
  "attribution": "Derived from Wikipedia ... (see LICENSE-DATA.md)",
  "records": [ ... sorted by destination, then area (null first) ... ]
}
```

`data/index.json`: `schema_version`, `generated_at`, `disclaimer`, `license`, `license_url`,
`attribution`, `passports: {ISO2: {file, source_title, source_url, source_revision,
source_timestamp, record_count, last_changed}}`. `data/all.json` is minified:
`{schema_version, generated_at, disclaimer, license, attribution, passports: {ISO2: [records]}}`.

Disclaimer text (verbatim in README and index.json):
"Visa data is community-sourced from Wikipedia and may be incomplete, outdated or wrong. Always
verify entry requirements with the official embassy or government source of the destination
before travelling."

## CLI (pipeline branch provides, workflow calls)

`python -m visa_pipeline run [--data data] [--state state] [--out out] [--only DE,US]
[--max-status-changes 15] [--max-record-drop-pct 10] [--force]`

- `data/` = published, committed output. Also the "previous run" for diffs.
- `state/` = committed run state: `pages.json` (discovered pages + mapping) and `revisions.json`.
- `out/` = gitignored run artifacts: `summary.json`, `report.md`, `changelog.md`.
- Exit 0 = ok (blocked passports allowed). Exit 1 = a hard failure (zero rows where rows existed
  before, an exception on a page, schema-invalid output). Good passports are still written before
  exiting 1.
- `out/summary.json`: `{"pages_found", "pages_mapped", "pages_unmapped": [...], "pages_parsed",
  "pages_skipped_unchanged", "rows", "blocked": [{"passport","reason"}], "failed":
  [{"passport","reason"}], "unmapped_statuses": [...], "unmapped_destinations": [...],
  "changes": n}`.

## Wikipedia access

Contact for the User-Agent comes from env `VISA_PIPELINE_CONTACT`, default
`https://github.com/Riedel-David/Visa-requirements`.
UA: `VisaApp-DataPipeline/<version> (<contact>)`. Only `https://en.wikipedia.org/w/api.php`.
