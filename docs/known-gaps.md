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
- **`special` status**: also covers government travel bans (for example `KR` to Iran or
  Ukraine) and undefined regimes (Western Sahara). The reason is in `notes`; for banned
  destinations `allowed_stay_days` may still be set from the underlying visa rule.
- **Multi-area territories**: Bonaire, Saba and Sint Eustatius (`BQ`) are published as area
  records only. For `SH`, the island of Saint Helena is the whole-country record
  (`area: null`) and Ascension and Tristan da Cunha are area records, so `area: null` on `SH`
  means the island of Saint Helena, not the whole group.
