"""Parse Wikipedia 'Visa requirements for X citizens' pages into Records."""
import re
from dataclasses import dataclass, field

import mwparserfromhell

from . import clean, countries, status, stay, table


@dataclass
class ParseResult:
    """Result of parsing a visa requirements page."""
    records: list[dict] = field(default_factory=list)
    unmapped_statuses: list[dict] = field(default_factory=list)
    unmapped_destinations: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_heading(heading: str) -> str:
    """Normalize a section heading for matching."""
    return heading.lower().strip().replace('_', ' ')


def _find_section_by_heading(wikicode, heading_keywords: list[str]) -> str | None:
    """Find a section whose heading exactly matches one of the keywords.

    Args:
        wikicode: Parsed wikitext (or string)
        heading_keywords: List of lowercase heading texts to match exactly

    Returns:
        Section wikitext or None
    """
    # Convert to string if it's wikicode
    full_text = str(wikicode)

    # Find all level-2 section headings
    lines = full_text.split('\n')
    section_start = None

    for i, line in enumerate(lines):
        # Level-2 heading
        if line.startswith('==') and not line.startswith('==='):
            heading = _normalize_heading(line.strip('= \n'))

            # Check if this heading exactly matches any of our keywords
            match = heading in heading_keywords

            if match and section_start is None:
                # Found the start of our section
                section_start = i
            elif section_start is not None:
                # Found the next same-level section - extract everything between
                section_lines = lines[section_start:i]
                return '\n'.join(section_lines)

    # If we found a section but reached end of file
    if section_start is not None:
        section_lines = lines[section_start:]
        return '\n'.join(section_lines)

    return None


def _find_all_subsections(wikicode, parent_heading_keywords: list[str]) -> list[tuple[str, str]]:
    """Find all level-3 subsections under a level-2 parent section.

    Args:
        wikicode: Parsed wikitext
        parent_heading_keywords: Keywords to identify the parent section

    Returns:
        List of (subsection_heading, subsection_text) tuples
    """
    # First find the parent section
    parent_section = _find_section_by_heading(wikicode, parent_heading_keywords)
    if not parent_section:
        return []

    # Parse the parent section and get level-3 subsections
    parent_wikicode = mwparserfromhell.parse(parent_section)
    subsections = parent_wikicode.get_sections(levels=[3], include_headings=True)

    result = []
    for subsection in subsections:
        subsection_text = str(subsection).strip()
        if not subsection_text:
            continue

        lines = subsection_text.split('\n', 1)
        if not lines[0].startswith('==='):
            continue

        heading = lines[0].strip('= \n')
        result.append((heading, subsection_text))

    return result


def _identify_columns(headers: dict[str, str]) -> dict[str, str]:
    """Identify column roles from header text.

    Args:
        headers: Dict of column_idx -> header_text

    Returns:
        Dict of role -> column_idx (e.g., {"destination": "0", "status": "1", ...})
    """
    roles = {}

    for col_idx, header_text in headers.items():
        header_lower = header_text.lower().strip()

        if any(kw in header_lower for kw in ['country', 'region', 'visitor to', 'territory', 'destination']):
            roles['destination'] = col_idx
        elif any(kw in header_lower for kw in ['visa requirement', 'conditions of access', 'visa status']):
            roles['status'] = col_idx
        elif any(kw in header_lower for kw in ['allowed stay', 'maximum stay', 'length of stay', 'stay']):
            roles['stay'] = col_idx
        elif 'notes' in header_lower or 'details' in header_lower:
            roles['notes'] = col_idx
        elif 'area' in header_lower:
            roles['area'] = col_idx

    return roles


def _extract_destination_and_area(cell_text: str, warnings: list[str]) -> tuple[str, str | None]:
    """Extract destination name and optional area from a destination cell.

    Handles cases like:
    - "{{flag|Japan}}" -> ("Japan", None)
    - "{{flag|Belarus}} - [[Brest]] and [[Grodno]]" -> ("Belarus", "Brest and Grodno")

    Args:
        cell_text: Raw cell text (will be cleaned)
        warnings: List to append warnings to

    Returns:
        (destination_name, area)
    """
    # Clean the text first
    cleaned = clean.clean(cell_text, warnings=warnings)

    # Check for area suffix (after - or –)
    if ' - ' in cleaned or ' – ' in cleaned:
        parts = re.split(r'\s+[-–]\s+', cleaned, maxsplit=1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()

    return cleaned.strip(), None


def _parse_table_rows(table_text: str, passport: str, section_name: str,
                     is_territory_or_restricted: bool, transclusions: dict[str, str],
                     source_url: str, source_revision: str,
                     result: ParseResult) -> None:
    """Parse a wikitable and add records to result.

    Args:
        table_text: Raw wikitable text
        passport: Passport code (e.g., "DE")
        section_name: Name of the section containing this table
        is_territory_or_restricted: Whether rows should be marked as territory/restricted
        transclusions: Transclusion dict for cleaning
        source_url: Source URL
        source_revision: Source revision ID
        result: ParseResult to append to (mutated)
    """
    rows = table.parse_table(table_text)
    if not rows:
        return

    # First row should be headers (unless it's a group label)
    headers = None
    data_rows = []

    for row in rows:
        if '_group_label' in row:
            # Skip group labels
            continue
        if headers is None:
            # This is the header row
            headers = row
        else:
            data_rows.append(row)

    if not headers or not data_rows:
        return

    # Identify column roles
    cleaned_headers = {k: clean.clean(v, transclusions, result.warnings) for k, v in headers.items()}
    roles = _identify_columns(cleaned_headers)

    # Check if this is a special German-style table (has Area column + status in "Maximum stay")
    has_area_column = 'area' in roles
    status_in_stay = False
    if has_area_column and 'status' not in roles and 'stay' in roles:
        # Check if the "stay" column actually contains status text
        sample_stay = data_rows[0].get(roles['stay'], '') if data_rows else ''
        if any(kw in sample_stay.lower() for kw in ['required', 'visa', 'permit']):
            status_in_stay = True

    # Parse data rows
    seen_keys = set()
    for row in data_rows:
        # Extract destination
        dest_col = roles.get('destination')
        if not dest_col or dest_col not in row:
            continue

        dest_name, area_from_cell = _extract_destination_and_area(
            row[dest_col], result.warnings
        )

        if not dest_name:
            continue

        # Look up country code
        dest_code = countries.lookup_country(dest_name)
        if not dest_code:
            result.unmapped_destinations.append({
                'passport': passport,
                'destination_name': dest_name,
                'section': section_name
            })
            continue

        # Handle area column or area from destination cell
        area = None
        if has_area_column and 'area' in roles and roles['area'] in row:
            area = clean.clean(row[roles['area']], transclusions, result.warnings).strip() or None
        elif area_from_cell:
            area = area_from_cell

        # Check for duplicate (destination, area) key
        key = (dest_code, area)
        if key in seen_keys:
            result.warnings.append(f"Duplicate key: {passport} -> {dest_name} ({dest_code}, {area})")
            continue
        seen_keys.add(key)

        # Extract status
        if status_in_stay:
            status_text = row.get(roles['stay'], '')
        else:
            status_text = row.get(roles.get('status', ''), '')

        status_cleaned = clean.clean(status_text, transclusions, result.warnings).strip()

        if not status_cleaned:
            # No status - skip this row
            continue

        primary_status, alternatives = status.parse_status(status_cleaned)

        # Track unmapped statuses
        if primary_status == 'special':
            result.unmapped_statuses.append({
                'passport': passport,
                'destination_name': dest_name,
                'raw_status': status_cleaned
            })

        # Extract stay
        stay_days = None
        stay_raw = None
        stay_note = None

        if status_in_stay:
            # No separate stay column in German special table
            pass
        elif 'stay' in roles and roles['stay'] in row:
            stay_text = row[roles['stay']]
            stay_raw = clean.clean(stay_text, transclusions, result.warnings).strip() or None
            if stay_raw:
                stay_days, stay_note = stay.parse_stay(stay_raw)

        # Extract notes
        notes_parts = []
        if 'notes' in roles and roles['notes'] in row:
            notes_text = row[roles['notes']]
            notes_cleaned = clean.clean(notes_text, transclusions, result.warnings).strip()
            if notes_cleaned:
                # Split bullets and join with newlines
                bullets = [line.strip() for line in notes_cleaned.split('\n') if line.strip()]
                # Remove leading * or •
                bullets = [re.sub(r'^[*•]\s*', '', b) for b in bullets]
                notes_parts.extend(bullets)

        # Add stay note if present
        if stay_note:
            notes_parts.append(stay_note)

        notes = '\n'.join(notes_parts) if notes_parts else None

        # Special case: Indian territories have no stay column but may have stay in first note
        if not stay_raw and not has_area_column and notes_parts:
            # Check if first note is purely a duration
            first_note = notes_parts[0]
            potential_days, potential_note = stay.parse_stay(first_note)
            if potential_days and not potential_note:
                stay_days = potential_days
                stay_raw = first_note
                # Remove this note from notes
                notes_parts = notes_parts[1:]
                notes = '\n'.join(notes_parts) if notes_parts else None

        # Build record
        record = {
            'passport': passport,
            'destination': dest_code,
            'destination_name': dest_name,
            'area': area,
            'status': primary_status,
            'alternative_statuses': alternatives,
            'allowed_stay_days': stay_days,
            'allowed_stay_raw': stay_raw,
            'notes': notes,
            'is_territory_or_restricted': is_territory_or_restricted,
            'source_url': source_url,
            'source_revision': source_revision
        }

        result.records.append(record)


def parse_page(wikitext: str, *, passport: str, title: str, revid: int,
               transclusions: dict[str, str]) -> ParseResult:
    """Parse a 'Visa requirements for X citizens' Wikipedia page.

    Args:
        wikitext: Full page wikitext
        passport: ISO 3166-1 alpha-2 code (e.g., "DE")
        title: Page title (e.g., "Visa requirements for German citizens")
        revid: Revision ID
        transclusions: Dict from transclusions.parse_template()

    Returns:
        ParseResult with records and diagnostics
    """
    result = ParseResult()
    source_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    source_revision = str(revid)

    wikicode = mwparserfromhell.parse(wikitext)

    # Find main "Visa requirements" section
    main_section_text = _find_section_by_heading(wikicode, ['visa requirements'])
    if main_section_text:
        # Look for table directly in this section
        if '{|' in main_section_text and '|}' in main_section_text:
            # Extract the first table
            table_match = re.search(r'\{\|.*?\|\}', main_section_text, re.DOTALL)
            if table_match:
                table_text = table_match.group(0)
                _parse_table_rows(
                    table_text, passport, 'Visa requirements',
                    is_territory_or_restricted=False,
                    transclusions=transclusions,
                    source_url=source_url,
                    source_revision=source_revision,
                    result=result
                )

    # Find territory/limited recognition subsections
    territory_keywords = [
        'territories', 'limited recognition', 'dependent', 'disputed', 'restricted territories'
    ]
    territory_subsections = _find_all_subsections(wikicode, territory_keywords)

    for subsection_heading, subsection_text in territory_subsections:
        # Parse tables in this subsection
        table_matches = re.finditer(r'\{\|.*?\|\}', subsection_text, re.DOTALL)
        for table_match in table_matches:
            table_text = table_match.group(0)
            _parse_table_rows(
                table_text, passport, subsection_heading,
                is_territory_or_restricted=True,
                transclusions=transclusions,
                source_url=source_url,
                source_revision=source_revision,
                result=result
            )

    # Find top-level "Special/Restricted areas" section (German pages)
    special_section_text = _find_section_by_heading(wikicode, ['special', 'restricted areas'])
    if special_section_text:
        table_matches = re.finditer(r'\{\|.*?\|\}', special_section_text, re.DOTALL)
        for table_match in table_matches:
            table_text = table_match.group(0)
            _parse_table_rows(
                table_text, passport, 'Special/Restricted areas',
                is_territory_or_restricted=True,
                transclusions=transclusions,
                source_url=source_url,
                source_revision=source_revision,
                result=result
            )

    # Deduplicate warnings
    result.warnings = list(dict.fromkeys(result.warnings))

    return result
