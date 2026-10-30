# Visa Requirements Dataset

[![CI](https://github.com/Riedel-David/Visa-requirements/actions/workflows/ci.yml/badge.svg)](https://github.com/Riedel-David/Visa-requirements/actions/workflows/ci.yml)
[![Update Data](https://github.com/Riedel-David/Visa-requirements/actions/workflows/update-data.yml/badge.svg)](https://github.com/Riedel-David/Visa-requirements/actions/workflows/update-data.yml)

A machine-readable dataset of global visa requirements, automatically generated from Wikipedia's "Visa requirements for X citizens" articles.

## ⚠️ Disclaimer

**Visa data is community-sourced from Wikipedia and may be incomplete, outdated or wrong. Always verify entry requirements with the official embassy or government source of the destination before travelling.**

## Consuming the Data

The dataset is published via GitHub Pages and updated weekly:

### Main Endpoints

- **Index**: `https://riedel-david.github.io/Visa-requirements/index.json`
  - Lists all available passports with metadata
  - Compare `source_revision` to detect data changes (it moves only when the visa data changes, not on every Wikipedia edit)
  
- **Per-passport files**: `https://riedel-david.github.io/Visa-requirements/passports/<ISO2>.json`
  - e.g., `passports/DE.json` for German passport holders
  - Contains all visa requirements for that passport
  
- **All data**: `https://riedel-david.github.io/Visa-requirements/all.json`
  - Single file with all passports (larger download)
  - Minified format

### Pinning a Specific Version

Data snapshots are tagged as `data-YYYY-MM-DD`. You can access a specific version via:

```
https://raw.githubusercontent.com/Riedel-David/Visa-requirements/data-2026-10-30/data/passports/DE.json
```

See [DATA_FORMAT.md](DATA_FORMAT.md) for detailed schema documentation.

## Data Format

Each passport file contains:

```json
{
  "schema_version": "1.0.0",
  "passport": "DE",
  "source_title": "Visa requirements for German citizens",
  "source_url": "https://en.wikipedia.org/wiki/...",
  "source_revision": "1379323599",
  "source_timestamp": "2026-10-09T12:34:56Z",
  "generated_at": "2026-10-30T06:00:00Z",
  "license": "CC BY-SA 4.0",
  "attribution": "Derived from Wikipedia... (see LICENSE-DATA.md)",
  "records": [...]
}
```

### Record Structure

Each record represents the visa requirement for one destination:

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
  "notes": "Additional details...",
  "is_territory_or_restricted": false,
  "source_url": "https://en.wikipedia.org/wiki/...",
  "source_revision": "1379323599"
}
```

## CSV Exports

Three CSV files are generated into `data/` at the end of every run (published next to `all.json`):

| File | Layout |
|------|--------|
| `passport-index-tidy-iso2.csv` | `Passport,Destination,Requirement`, one row per passport and destination, ISO-2 codes |
| `passport-index-tidy-iso3.csv` | same, ISO-3 codes |
| `passport-index-matrix-iso2.csv` | first column `Passport`, one column per destination, cell = requirement |

- Only the whole-country record (`area` is null) is used. `Requirement` is our `status` value as is:
  `visa_free`, `visa_on_arrival`, `eta`, `evisa`, `visa_required`, `permit_required`,
  `admission_refused`, `special`. No stay days, no notes.
- Missing passport/destination pairs have no row in the tidy files and an empty cell in the matrix.
- Rows and columns are sorted by ISO-2 code, so identical input gives byte-identical files.
- ISO-3 codes come from the static table `src/visa_pipeline/iso3.json`. Codes without an ISO-3
  (the X-codes) are kept as is, except Kosovo: `XK` becomes `XKX` (user-assigned). `XN`, `XS`, `XA`,
  `XO`, `XT` and `XW` stay two-letter in the ISO-3 file.

## Status Mapping

The pipeline normalizes Wikipedia's visa status descriptions into these categories:

| Status | Meaning |
|--------|---------|
| `visa_free` | No visa required, including freedom of movement |
| `visa_on_arrival` | Visa issued at the port of entry |
| `eta` | Electronic Travel Authorization required |
| `evisa` | Electronic visa (eVisa) required |
| `visa_required` | Traditional visa required (must apply in advance) |
| `permit_required` | Special permit required (e.g., for restricted areas) |
| `admission_refused` | Entry not permitted |
| `special` | Unmapped or special case (see `notes` field) |

### Combined Statuses

When Wikipedia lists multiple options (e.g., "eVisa / Visa on arrival"):
- `status` contains the **least restrictive** option
- `alternative_statuses` lists the other options in order

## Overrides and X-Codes

### Destination Aliases

The pipeline uses `src/visa_pipeline/overrides/destinations.json` to:
- Map destination names to ISO 3166-1 alpha-2 codes
- Handle territories and disputed regions
- Assign user-defined X-codes for non-ISO destinations:
  - **XK** - Kosovo
  - **XN** - Northern Cyprus
  - **XS** - Somaliland
  - **XA** - Abkhazia
  - **XO** - South Ossetia
  - **XT** - Transnistria
  - **XW** - Sahrawi Arab Democratic Republic (Western Sahara itself is `EH`)
  
See the overrides file for the complete list of X-codes.

### Passport Mapping

`src/visa_pipeline/overrides/passports.json` maps Wikipedia article titles to passport ISO codes.

## Safety Mechanisms

The pipeline includes safety checks to prevent publishing bad data:

- **Status change threshold**: Max 15 status changes per passport
- **Record drop threshold**: Max 10% drop in record count
- **Zero-row detection**: Flags passports with no data when previous data existed

When a threshold is exceeded:
- The old data is kept (not overwritten)
- A GitHub issue is opened automatically
- The workflow still completes (other passports are processed)

Override with CLI flags:
```bash
python -m visa_pipeline run --force  # Bypass all thresholds
python -m visa_pipeline run --max-status-changes 20 --max-record-drop-pct 15
```

## How It Works

1. **Discovery**: Finds "Visa requirements for X citizens" articles from Wikipedia's category system
2. **Revision check**: Compares article revisions against stored state to skip unchanged pages
3. **Parsing**: Extracts visa requirements from wikitext tables using `mwparserfromhell`
4. **Status mapping**: Normalizes visa status text to the enum (unmapped statuses → `special` + report)
5. **Validation**: Checks data quality with JSON Schema and safety thresholds
6. **Publishing**: Generates per-passport JSON files, index, and changelog

The pipeline:
- Uses only the Wikipedia MediaWiki API (no scraping)
- Follows API politeness guidelines (User-Agent, serial requests, `maxlag`, `Retry-After`)
- Resolves transcluded notes by fetching `Template:Transcluded sections for the visa articles`
- Handles complex table structures (colspan/rowspan, data-sort-value attributes)

## Running Locally

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Run the Pipeline

```bash
# Process all passports
python -m visa_pipeline run --data data --state state --out out

# Process specific passports only
python -m visa_pipeline run --only DE,US,FR

# Force update (ignore revision checks)
python -m visa_pipeline run --force
```

### Run Tests

```bash
.venv/bin/pytest -q
```

### Lint

```bash
.venv/bin/python -m pyflakes src tests
```

## Automated Updates

The dataset is updated automatically via GitHub Actions:

- **Schedule**: Every Monday at 04:17 UTC
- **Manual trigger**: Via workflow_dispatch (supports `--force` and `--only` options)
- **On changes**: Data and state are committed to `main` with a `data-YYYY-MM-DD` tag
- **On issues**: An issue is opened/updated when blocked passports or unmapped statuses are detected
- **Deployment**: Published to GitHub Pages automatically

### Why Commit Data to Main?

Unlike some datasets that store only the generation pipeline, this repo commits the data to `main` because:
- **Versioned history**: Git tracks exactly when and how visa rules changed
- **Diffable**: Changes are visible in commit diffs
- **Pinnable**: Consumers can pin to specific data tags
- **Reliable**: The committed data is the source of truth (no risk of ephemeral artifact loss)

## License and Attribution

### Code License

The source code (pipeline, scripts, tests) is licensed under the [MIT License](LICENSE).

### Data License

The visa data in `data/` is derived from Wikipedia and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

See [LICENSE-DATA.md](LICENSE-DATA.md) for full attribution requirements.

**Summary for app developers:**
- Credit "Wikipedia contributors"
- Link to the source article (provided in each passport file)
- Link to CC BY-SA 4.0 license
- State that the data was transformed/normalized
- Display attribution and disclaimer in your app

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Important**: Data corrections should be made on Wikipedia first, as this repository mirrors Wikipedia content. Only report parsing bugs or systematic issues here.

## Status

This project is actively maintained. The pipeline runs weekly, and data is updated automatically.

## Related Resources

- [Wikipedia Visa Requirement Articles](https://en.wikipedia.org/wiki/Category:Visa_requirements_by_nationality)
- [DATA_FORMAT.md](DATA_FORMAT.md) - Detailed schema documentation
- [GitHub Actions Workflows](.github/workflows/) - Automation details
