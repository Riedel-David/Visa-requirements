# Data Format Documentation

This document describes the JSON schema for the visa requirements dataset, intended for developers consuming the data.

## Overview

The dataset is published in three main formats:

1. **`index.json`** - Metadata about all available passports
2. **`passports/<ISO2>.json`** - Per-passport visa requirements (e.g., `passports/DE.json`)
3. **`all.json`** - All passports in a single file (minified). Not committed to git; available on GitHub Pages and as a GitHub Release asset

All files are served via GitHub Pages: `https://riedel-david.github.io/Visa-requirements/`

## JSON Schema

The authoritative JSON Schema is available at: `src/visa_pipeline/schema/passport.schema.json`

## File Formats

### `index.json`

Provides metadata for all passports and helps detect changes:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-10-30T06:00:00Z",
  "disclaimer": "Visa data is community-sourced from Wikipedia...",
  "license": "CC BY-SA 4.0",
  "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
  "attribution": "Derived from Wikipedia contributors...",
  "passports": {
    "DE": {
      "file": "passports/DE.json",
      "source_title": "Visa requirements for German citizens",
      "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
      "source_revision": "1379323599",
      "source_timestamp": "2026-10-09T12:34:56Z",
      "record_count": 245,
      "last_changed": "2026-10-23T06:00:00Z"
    },
    "US": { ... },
    ...
  }
}
```

**Usage**: Compare `source_revision` to detect if a passport's data has changed. It moves only when the visa data changes, not on every Wikipedia edit.

### `passports/<ISO2>.json`

Individual passport file with all visa requirements:

```json
{
  "schema_version": "1.0.0",
  "passport": "DE",
  "source_title": "Visa requirements for German citizens",
  "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
  "source_revision": "1379323599",
  "source_timestamp": "2026-10-09T12:34:56Z",
  "generated_at": "2026-10-30T06:00:00Z",
  "license": "CC BY-SA 4.0",
  "attribution": "Derived from Wikipedia contributors (see LICENSE-DATA.md)",
  "records": [
    {
      "passport": "DE",
      "destination": "JP",
      "destination_name": "Japan",
      "area": null,
      "status": "visa_free",
      "alternative_statuses": [],
      "allowed_stay_days": 90,
      "allowed_stay_raw": "90 days",
      "notes": "90 days within any 180-day period",
      "is_territory_or_restricted": false,
      "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
      "source_revision": "1379323599"
    },
    ...
  ]
}
```

Records are sorted by `destination`, then `area` (null first).

### `all.json`

All passports in one file (minified):

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-10-30T06:00:00Z",
  "disclaimer": "Visa data is community-sourced from Wikipedia...",
  "license": "CC BY-SA 4.0",
  "attribution": "Derived from Wikipedia contributors...",
  "passports": {
    "DE": [ /* records array */ ],
    "US": [ /* records array */ ],
    ...
  }
}
```

## CSV Exports

Three CSV files are generated into `data/` at the end of every run. They are not committed to git: download them from the GitHub Release (or GitHub Pages, next to `all.json`):

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

## Record Fields

Each record represents the visa requirement for one destination (or destination area):

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `passport` | string | No | Passport country (ISO 3166-1 alpha-2) |
| `destination` | string | No | Destination country (ISO 3166-1 alpha-2 or X-code) |
| `destination_name` | string | No | Human-readable destination name |
| `area` | string | Yes | Sub-national area (e.g., "Tibet Autonomous Region"), null for whole country |
| `status` | enum | No | Visa status (see Status Enum below) |
| `alternative_statuses` | array | No | Alternative visa options (e.g., ["evisa"] when status is "visa_on_arrival") |
| `allowed_stay_days` | integer | Yes | Maximum stay duration in days, null if not specified or varies |
| `allowed_stay_raw` | string | Yes | Original stay text from Wikipedia (e.g., "3 months", "Unlimited") |
| `notes` | string | Yes | Additional details, cleaned and normalized |
| `is_territory_or_restricted` | boolean | No | Whether this is a territory/disputed region/restricted area |
| `source_url` | string | No | Wikipedia article URL |
| `source_revision` | string | No | Wikipedia revision ID at which this passport's data last changed (may lag the live page: edits that leave the visa data identical do not rewrite the file) |

### Unique Key

Within a passport file, records are unique by `(destination, area)`. Most records have `area: null`.

## Status Enum

| Status | Meaning |
|--------|---------|
| `visa_free` | No visa required (includes freedom of movement zones) |
| `visa_on_arrival` | Visa issued at the port of entry |
| `eta` | Electronic Travel Authorization required |
| `evisa` | Electronic visa required |
| `visa_required` | Traditional visa required (must apply in advance) |
| `permit_required` | Special permit required |
| `admission_refused` | Entry not permitted |
| `special` | Unmapped or special case (check `notes` for details) |

### Status Ordering

Statuses are ordered from least to most restrictive:
```
visa_free < visa_on_arrival < eta < evisa < visa_required < permit_required < admission_refused
```

`special` sits outside the ordering and represents unmapped cases.

### Combined Statuses

When Wikipedia lists multiple options (e.g., "eVisa / Visa on arrival"):
- `status` contains the **least restrictive** option (`visa_on_arrival`)
- `alternative_statuses` contains the others in order (`["evisa"]`)

### Status Mapping

The mapping table is `STATUS_MAP` in `src/visa_pipeline/status.py`.

- Mapping is by the cell **text**, not the template colour: `{{free|Visa required}}` exists and maps to `visa_required`.
- In a combined cell, `status` is the least restrictive option because the traveller can pick the easiest one listed; the others remain available and are kept in `alternative_statuses`.
- If any part of a combined cell is unmapped, the whole cell becomes `special` (no guessing from the remaining parts). Unmapped text is reported on every run.

Judgement calls:

| Wikipedia text | Status | Why |
|----------------|--------|-----|
| `e-VOA`, `Electronic visa on arrival` | `visa_on_arrival` | Approval/payment happens at the border |
| `Ease`, `Pre-registration required` | `eta` | Online registration, not a visa |
| `ID card` | `visa_free` | Entry without a visa on an ID card |
| `Easy visitor permit`, `Visitor's pass required` | `permit_required` | A permit must be obtained |
| `Travel banned` | `special` | Usually the home government forbids travel, not the destination |

## X-Codes (Non-ISO Destinations)

For destinations without ISO 3166-1 alpha-2 codes, user-assigned X-codes are used:

| Code | Destination |
|------|-------------|
| XK | Kosovo |
| XN | Northern Cyprus |
| XS | Somaliland |
| XA | Abkhazia |
| XO | South Ossetia |
| XT | Transnistria |
| XW | Sahrawi Arab Democratic Republic (Western Sahara itself is `EH`) |

The mapping is defined in `src/visa_pipeline/overrides/destinations.json`.

## Schema Versioning

The `schema_version` field follows semantic versioning:

- **Major version** changes indicate breaking changes (field removal, type changes, enum changes)
- **Minor version** changes indicate backward-compatible additions (new fields, new enum values)
- **Patch version** changes indicate documentation or non-breaking fixes

Current version: `1.0.0`

## Stability Guarantees

- Field names and types are stable within a major version
- The status enum may expand with new values (minor version bump)
- Records may have `null` for nullable fields (always check before accessing)
- The `notes` field is free-form text and should not be parsed programmatically

## Example: Kotlin/Android Consumption

```kotlin
// 1. Fetch index.json and compare revisions
val index = fetchJson("https://riedel-david.github.io/Visa-requirements/index.json")
val deMetadata = index.passports["DE"]
if (deMetadata.source_revision != cachedRevision) {
    // 2. Download the updated passport file
    val passport = fetchJson("https://riedel-david.github.io/Visa-requirements/passports/DE.json")
    
    // 3. Process records
    passport.records.forEach { record ->
        when (record.status) {
            "visa_free" -> showVisaFree(record)
            "visa_required" -> showVisaRequired(record)
            "special" -> showSpecialCase(record.notes)
            // ... handle other statuses
        }
    }
}
```

## Data Attribution

The data is licensed under CC BY-SA 4.0. See [LICENSE-DATA.md](LICENSE-DATA.md) for full attribution requirements.

**Your app must display:**
1. Attribution to Wikipedia contributors
2. Link to the source article (from `source_url`)
3. Link to CC BY-SA 4.0 license
4. The disclaimer: "Visa data is community-sourced from Wikipedia and may be incomplete, outdated or wrong. Always verify entry requirements with the official embassy or government source of the destination before travelling."

## Disclaimer

This data is provided as-is without warranty. Always verify visa requirements with official government sources before travelling.
