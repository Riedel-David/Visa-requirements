# Parser design (step 1 findings, 2026-10-30)

Fixtures: `tests/fixtures/Visa_requirements_for_{German,United_States,Indian}_citizens.wikitext`
(+ `.meta.json` with revid). Fetched with `scripts/fetch_fixture.py`.

## Structure differences found

| | DE | US | IN |
|---|---|---|---|
| Main table section | "Visa requirements" | same | same |
| Main table columns | Country/Region, Visa requirement, Allowed stay, Notes, Reciprocity | same 5 | **4** (no Reciprocity) |
| Main rows | 193 | 193 | 193 |
| Territories subsection | "Requirements for entry to territories and states with limited recognition" | "Territories or administrative subdivisions with different visa policies" | "Dependent, disputed, or restricted territories" |
| Territories tables | 1, 4 cols, region header rows (`! colspan=4 \| Europe`) | 1, 4 cols, region header rows | **2** tables, **3 cols (no Allowed stay; stay is in Notes as "* 30 days")**; 2nd table groups by sovereign (`! colspan=4 \| China`) and uses `\| colspan=2 \| {{flag\|...}}` |
| Special/Restricted areas | separate table: Country, **Area**, Maximum stay (holds status!), Details | none | none |
| Sort keys | `{{sort\|90\|90 days}}`, `{{sort\|EU\|...}}` inside status | `data-sort-value="365" \| 1 year` cell attribute | `data-sort-value="4" {{no\|...}}` **without the `\|` separator** (attribute glued to content) |
| Secondary sections | Vaccination (yellow fever/polio/meningococcal tables), Passport requirements, Entry bans | none | none |

Common to all:
- Status = colour template wrapping text: `{{yes|..}}`, `{{yes2|..}}`, `{{no|..}}`, `{{no2|..}}`,
  `{{free|..}}`, `{{Optional|..}}`, `{{yes-no|..}}`, `{{BLACK|style=..|Admission refused}}`,
  `{{n/a|..}}`, sometimes wrapping `{{sort|key|text}}` or `[[link|text]]`. Template name is a
  colour, not semantics — "Visa required" appears under both `no` and `free`; map on **text**.
- Destination = `{{flag|Name}}` / `{{flagu|..}}` / `{{flagicon|..}}`, sometimes followed by a
  region (`{{flag|Belarus}} - [[Brest]] and [[Grodno]]`).
- Notes are bullet lists, often with `<ref>`, `{{cn}}`, and **transclusions**
  `{{#section-h::Template:Transcluded sections for the visa articles|Algeria. VOA}}` (16 in DE,
  15 US, 12 IN). That template page has 46 named sections and must be fetched once per run.
- Multi-row cells (`rowspan`) don't occur in these three pages; handle them anyway.

## Proposed design

```
src/visa_pipeline/
  api.py          MediaWiki client: UA w/ contact, serial, maxlag=5, Retry-After, backoff
  discover.py     category members -> titles; demonym->ISO2 via overrides + country-name table
  sections.py     find sections by heading (normalised, alias list), not index
  table.py        generic wikitable -> grid of cells (handles colspan/rowspan, `!!`/`||`,
                  header rows, cell attributes incl. glued `data-sort-value="4" {{..}}`)
  clean.py        mwparserfromhell: drop <ref>/cite/cn/sort-key, resolve [[A|B]], unwrap
                  colour templates, resolve #section-h from the fetched template
  status.py       ONE mapping table: normalised text -> enum, ordered rules, unmapped -> special+report
  stay.py         raw -> days (90 days, 3 months=90, 1 year=365, "30 days within 180" -> 30
                  + note, Unlimited/FoM -> null + note)
  countries.py    destination name -> ISO2 (static table + data/overrides/destinations.json)
  extract_main.py column roles detected from header text (destination / status / stay / notes /
                  area), so 3-, 4- and 5-column tables share one code path
  extract_extra.py vaccination, passport validity/blank pages, entry bans (after main is solid)
  validate.py     JSON Schema + diff thresholds (N=15 status changes, -10% rows, zero rows)
  publish.py      per-passport files, index.json, all.json, changelog
```

Key decisions:
1. **Column roles from headers**, not position: match header text ("visa requirement"/"conditions
   of access" -> status, "allowed stay"/"maximum stay" -> stay, "notes"/"details" -> notes,
   "area" -> sub-area). When there is no stay column (IN territories), try to parse stay
   from the first note bullet.
2. **Status mapped from cleaned text**, not template colour. Template name kept only as a
   tie-breaker (e.g. `BLACK` -> admission_refused).
3. **Territory flag**: rows from the subsection tables and Special/Restricted areas get
   `is_territory_or_restricted: true`; a restricted area gets destination = sovereign ISO2 plus
   `destination_name` "China – Tibet Autonomous Region" (record key = passport+destination+area).
   A territory-section row with no area that collides with a whole-country row of a different
   status never replaces it: it is stored with the section heading as `area` (e.g. KZ Baikonur
   permit under "Territories and disputed areas") and a `SPLITTING` warning.
4. **ISO codes for non-ISO destinations** (Abkhazia, Kosovo, Northern Cyprus, Somaliland...):
   use user-assigned codes from an override file (`XK` is conventional for Kosovo; others get
   `X?` codes or null + report). Needs your decision — see question.
5. **Transcluded notes**: fetch the template page once per run, split by heading, substitute.
6. **Publishing (proposed)**: deploy as a Pages artifact, no data commits. Previous state =
   the currently published site: the run downloads live `index.json` (revids) and
   `passports/*.json` (previous records for the diff/threshold check) and fails loudly if it
   can't. The published data is then the only source of truth, so state can't drift from what
   apps see. Alternative: commit `data/` back to `main` daily (git diff history of the data,
   but noisy commits).

## Decisions (2026-10-30)

- This repo is a public, self-updating dataset. The app consumes it at build time (option a), so no
  runtime download is needed.
- Weekly GitHub Action auto-commits `data/` to `main` and pushes a `data-YYYY-MM-DD` tag. Pages
  serves `data/`. Passports blocked by the safety check keep their old data, and the run opens or
  updates a GitHub issue.
- Combined statuses: `status` holds the least restrictive option, and `alternative_statuses`
  lists the rest (e.g. "eVisa / Visa on arrival" -> visa_on_arrival + ["evisa"]).
- Non-ISO destinations: X-codes come from `overrides/destinations.json`, reusing the app's
  XK/XN/XS, and are documented in the README. Nothing is dropped silently.
- User-Agent contact defaults to the repo URL (no email in a public repo); override with
  `VISA_PIPELINE_CONTACT`.
- Code licence: open (MIT recommended). Data: CC BY-SA 4.0.
