# Parser Test Report

Generated: 2026-10-30 11:54:11

This report summarizes the parser's performance across all 8 test fixtures after
completing territory coverage, combined cell parsing, and status mapping improvements.

## Summary

| Fixture | Main | Territory | Restricted (area set) | Unmapped Dest | Unmapped Status |
|---------|------|-----------|----------------------|---------------|-----------------|
| DE | 193 | 90 | 42 | 2 | 0 |
| US | 194 | 80 | 33 | 0 | 0 |
| IN | 193 | 51 | 6 | 0 | 0 |
| GB | 193 | 79 | 31 | 3 | 0 |
| AE | 193 | 54 | 6 | 0 | 0 |
| AF | 193 | 47 | 14 | 4 | 0 |
| BR | 193 | 53 | 5 | 0 | 0 |
| JP | 193 | 85 | 40 | 3 | 0 |

**Key achievements:**
- All 8 fixtures now have territory/restricted records (was 0 for GB/AE/AF/BR)
- Combined country+region cells (e.g., 'Norway Jan Mayen') now parse correctly
- Area-aware deduplication prevents whole-country rows from being removed
- Most fixtures have ≤3 unmapped destinations (unavoidable edge cases)
- Most fixtures have 0 unmapped statuses

---

## German (DE)

- **Total records**: 283
  - Main table: 193
  - Territory/Restricted: 90 (42 with area)

### Status Breakdown

- `visa_free`: 164
- `eta`: 15
- `evisa`: 30
- `visa_on_arrival`: 27
- `visa_required`: 14
- `permit_required`: 33

### Unmapped Items

**Destinations** (2):

- United Nations *(section: Special/Restricted areas)*
- United Nations *(section: Special/Restricted areas)*

---

## United_States (US)

- **Total records**: 274
  - Main table: 194
  - Territory/Restricted: 80 (33 with area)

### Status Breakdown

- `visa_free`: 155
- `eta`: 12
- `evisa`: 30
- `visa_on_arrival`: 33
- `visa_required`: 15
- `permit_required`: 22
- `admission_refused`: 3
- `special`: 4

### Unmapped Items

**Count**: 0 ✓

---

## Indian (IN)

- **Total records**: 244
  - Main table: 193
  - Territory/Restricted: 51 (6 with area)

### Status Breakdown

- `visa_free`: 36
- `eta`: 5
- `evisa`: 55
- `visa_on_arrival`: 24
- `visa_required`: 115
- `permit_required`: 6
- `special`: 3

### Unmapped Items

**Count**: 0 ✓

---

## British (GB)

- **Total records**: 272
  - Main table: 193
  - Territory/Restricted: 79 (31 with area)

### Status Breakdown

- `visa_free`: 159
- `eta`: 13
- `evisa`: 30
- `visa_on_arrival`: 31
- `visa_required`: 16
- `permit_required`: 23

### Unmapped Items

**Destinations** (3):

- United Nations *(section: Territories and disputed areas)*
- United Nations *(section: Territories and disputed areas)*
- United Nations *(section: Territories and disputed areas)*

---

## Emirati (AE)

- **Total records**: 247
  - Main table: 193
  - Territory/Restricted: 54 (6 with area)

### Status Breakdown

- `visa_free`: 154
- `eta`: 9
- `evisa`: 20
- `visa_on_arrival`: 38
- `visa_required`: 20
- `permit_required`: 5
- `special`: 1

### Unmapped Items

**Count**: 0 ✓

---

## Afghan (AF)

- **Total records**: 240
  - Main table: 193
  - Territory/Restricted: 47 (14 with area)

### Status Breakdown

- `visa_free`: 9
- `eta`: 4
- `evisa`: 54
- `visa_on_arrival`: 16
- `visa_required`: 144
- `permit_required`: 11
- `special`: 2

### Unmapped Items

**Destinations** (4):

- Flag_of_China.svg *(section: Territories and disputed areas)*
- UN *(section: Territories and disputed areas)*
- United Nations *(section: Territories and disputed areas)*
- United Nations *(section: Territories and disputed areas)*

---

## Brazilian (BR)

- **Total records**: 246
  - Main table: 193
  - Territory/Restricted: 53 (5 with area)

### Status Breakdown

- `visa_free`: 145
- `eta`: 6
- `evisa`: 32
- `visa_on_arrival`: 30
- `visa_required`: 26
- `permit_required`: 6
- `special`: 1

### Unmapped Items

**Count**: 0 ✓

---

## Japanese (JP)

- **Total records**: 278
  - Main table: 193
  - Territory/Restricted: 85 (40 with area)

### Status Breakdown

- `visa_free`: 159
- `eta`: 18
- `evisa`: 25
- `visa_on_arrival`: 37
- `visa_required`: 17
- `permit_required`: 21
- `special`: 1

### Unmapped Items

**Destinations** (3):

- United Nations *(section: Territories, disputed areas or restricted zones)*
- United Nations *(section: Territories, disputed areas or restricted zones)*
- United Nations *(section: Territories, disputed areas or restricted zones)*

---

## Notes

### Unmapped Destinations Explained

Most remaining unmapped destinations are expected edge cases:

1. **United Nations zones** (Korean DMZ, UNDOF zones, etc.)
   - Not real countries, but special international zones
   - Appear in multiple fixtures (DE, GB, JP)

2. **Cleaning artifacts in AF fixture**
   - 'Flag_of_China.svg', 'UN' - wikitext that wasn't fully cleaned
   - Could be fixed with additional template handling

All other fixtures have 0 unmapped destinations or only unavoidable edge cases.

### Unmapped Statuses Explained

Only 1 fixture (AF) has unmapped statuses:

- **Australia: 'Authoristion required'** - This is a typo variant that was mapped after detection

All other status texts successfully mapped to enum values.

### Territory/Restricted Records

Territory sections are now discovered at any level using pattern matching:
- Pattern: `/territor|disputed|restricted|limited recognition|autonomous/i`
- Descendants of main 'Visa requirements' section
- Standalone sections matching the pattern

Area field is set for:
- Cells with explicit area column (German 'Special areas')
- Combined country+region cells (`{{flag|Norway}} [[Jan Mayen]]` -> NO + area='Jan Mayen')
- Special territories (Ascension Island -> SH + area='Ascension Island')

### Deduplication

Keys are (destination, area) pairs:
- Only exact matches deduplicate
- Russia with no area ≠ Russia with area='closed cities'
- Warnings show both sections: 'first in X, dropped from Y'

