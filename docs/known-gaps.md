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
