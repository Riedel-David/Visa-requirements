# Known gaps in the published data

Places where the dataset is deliberately incomplete. A consumer should treat a missing
record as "unknown", never as "visa required".

- **Northern Cypriot citizens (`XN`)**: the Wikipedia page lists a single country (Turkey).
  The file has one record because the source has one.
- **Chinese citizens (`CN`) to Hong Kong, Macau and Taiwan**: the source uses a differently
  shaped table (in-lieu documents, conditional permits) and the Taiwan part has no
  destination column. Not parsed, because any single status would misstate the rule.
- **Hong Kong citizens (`HK`) to mainland China, Macau, Taiwan**: these sit in a "Greater
  China" section the parser does not read, and the status depends on a permit.
- **`special` status**: covers undefined regimes (Western Sahara) and cells whose text is not
  in the status table; the reason is in `notes`. Government travel bans are `travel_ban` when
  the source cell reads `Travel banned` or `Travel prohibited` (stay days are null). A ban
  described only in the notes under another status text (for example `KR` to Iran or
  Ukraine, if the cell does not say "banned") stays `special` until the source text changes.
- **Multi-area territories**: Bonaire, Saba and Sint Eustatius (`BQ`) are published as area
  records only. For `SH`, the island of Saint Helena is the whole-country record
  (`area: null`) and Ascension and Tristan da Cunha are area records, so `area: null` on `SH`
  means the island of Saint Helena, not the whole group.
- **Partial bans**: "Travel banned in most areas" (Niger) stays `special`; it is not a full ban
  and we do not guess.
- **Restricted zones** (for example Russia): rows for restricted areas carry the section name
  as `area`.
- **Unmapped statuses stay `special`** (about 70 distinct texts, reported in every run
  report): multi-line cells, "Visa not ...", stay-in-status values and the like. Decide per
  case only if a consumer needs one; add it to `status.py`, never a one-off patch.
- **Nagorno-Karabakh** (as a destination, for example from `JO`) stays unmapped on purpose:
  disputed and no ISO code.
- **Armenia to Kosovo**: Wikipedia contradicts itself (main table says visa required,
  territories table says visa free). The whole-country record is `visa_required`; the other
  claim is a separate area record.
- **Unverified**: destination `US` in the `BH` and `BZ` territory sections was never
  investigated (no fixtures). The main-page table regex `\{\|.*?\|\}` is non-greedy, so nested
  tables would break it.

## Policy

No hand-written data overrides for single rows. A fix must come from generic parsing of
Wikipedia, so the dataset keeps itself up to date without maintenance. The override files
only carry name/code mappings and ignore lists.

## Not started

- Secondary datasets (vaccination, passport validity, entry bans).
- Integrating the data into the Beyond-Borders app is a separate task in that repo.

## Verify after the next forced Update Data run (delete once checked)

Croatia about 259 records; China to the UK has a whole-country row; Italy to Saint Pierre and
Miquelon is its own record; `data/status.json` exists; Korea shows 17 `travel_ban` records; the
first scheduled run makes a "Refresh status.json" commit.
