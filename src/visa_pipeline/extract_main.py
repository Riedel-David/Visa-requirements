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
    _seen_keys: dict = field(default_factory=dict)  # Track (destination, area) -> (record_index, section_name, status, is_territory)


def _normalize_heading(heading: str) -> str:
    """Normalize a section heading for matching."""
    return heading.lower().strip().replace('_', ' ')


def _extract_section_hierarchy(wikitext: str) -> list[dict]:
    """Extract all sections from wikitext with their hierarchy.

    Returns:
        List of dicts with keys: level, heading, start_line, end_line
    """
    lines = wikitext.split('\n')
    sections = []

    for i, line in enumerate(lines):
        # Detect heading level
        if line.startswith('===='):
            level = 4
        elif line.startswith('==='):
            level = 3
        elif line.startswith('=='):
            level = 2
        else:
            continue

        heading = line.strip('= \n')
        sections.append({
            'level': level,
            'heading': heading,
            'start_line': i,
            'end_line': None  # Will be filled in next pass
        })

    # Fill in end_line for each section (ends where next same-or-higher-level section starts)
    for i, section in enumerate(sections):
        # Find next section at same or higher level
        for j in range(i + 1, len(sections)):
            if sections[j]['level'] <= section['level']:
                section['end_line'] = sections[j]['start_line']
                break
        # If no next section found, goes to end of file
        if section['end_line'] is None:
            section['end_line'] = len(lines)

    # Add text content
    for section in sections:
        section['text'] = '\n'.join(lines[section['start_line']:section['end_line']])

    return sections


def _is_territory_section(heading: str) -> bool:
    """Check if a heading indicates a territory/disputed area section."""
    heading_lower = heading.lower()

    # Exclude certain patterns
    if 'non-visa restriction' in heading_lower:
        return False

    # Match territory-related keywords (as whole words or phrases)
    patterns = [
        r'\bterritor',
        r'\bdisputed',
        r'\brestricted',
        r'\blimited recognition',
        r'\bspecial[/\s]+restricted',
        r'\bautonomous',
        r'\bdependent',
    ]

    return any(re.search(pattern, heading_lower) for pattern in patterns)


def _find_all_territory_sections(sections: list[dict], main_section_start: int) -> list[dict]:
    """Find all territory-related sections.

    Returns (in page order) every section that is a descendant of the main
    section, matches the territory pattern, or is a descendant of a section
    matching it. Callers parse each section's direct content only, so a table
    is never read twice through a parent section.
    """
    def is_descendant(child: dict, parent: dict) -> bool:
        return (parent['start_line'] < child['start_line'] < parent['end_line']
                and child['level'] > parent['level'])

    main = next((s for s in sections if s['start_line'] == main_section_start), None)
    matching = [s for s in sections if _is_territory_section(s['heading'])]

    territory_sections = []
    for section in sections:
        if section is main:
            continue
        if (section in matching
                or (main is not None and is_descendant(section, main))
                or any(is_descendant(section, m) for m in matching)):
            territory_sections.append(section)

    return territory_sections


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
        elif any(kw in header_lower for kw in ['visa requirement', 'entry requirement', 'conditions of access', 'visa status', 'requirement']):
            roles['status'] = col_idx
        elif any(kw in header_lower for kw in ['passport']) and 'status' not in roles:
            # Column with "passport" (e.g., "Regular passports") is a status column if no other status column found yet
            # This handles multi-passport-type tables like Northern Cyprus
            roles['status'] = col_idx
        elif any(kw in header_lower for kw in ['allowed stay', 'maximum stay', 'length of stay', 'stay']):
            roles['stay'] = col_idx
        elif 'notes' in header_lower or 'details' in header_lower:
            roles['notes'] = col_idx
        elif 'area' in header_lower:
            roles['area'] = col_idx

    return roles


def _is_decorative_flag(template) -> bool:
    """True for a flag template that carries only an image, not a country name."""
    name = template.name.strip().lower().replace('_', ' ')
    if 'flag' not in name:
        return False
    if not template.has(1):
        return True
    param1 = str(template.get(1).value).strip()
    return param1.lower() in ('image', 'un') or param1.endswith('.svg')


def _extract_destination_and_area(cell_text: str, warnings: list[str]) -> tuple[str, str | None]:
    """Extract destination name and optional area from a destination cell.

    Handles cases like:
    - "{{flag|Japan}}" -> ("Japan", None)
    - "{{flag|Norway}} [[Jan Mayen]]" -> ("Norway", "Jan Mayen")
    - "{{flagicon|Spain}} [[Canary Islands]]" -> ("Spain", "Canary Islands")
    - "{{flag|Belarus}} - [[Brest]] and [[Grodno]]" -> ("Belarus", "Brest and Grodno")

    Args:
        cell_text: Raw cell text (wikitext with templates)
        warnings: List to append warnings to

    Returns:
        (destination_name, area)
    """

    # Try to parse with mwparserfromhell to extract templates
    wikicode = mwparserfromhell.parse(cell_text)

    # Look for flag templates
    flag_country = None
    selected_node = None
    for template in wikicode.ifilter_templates():
        name = template.name.strip().lower().replace('_', ' ')
        if any(flag in name for flag in ['flag', 'flagicon', 'flagcountry']):
            # Extract country from first param
            if template.has(1):
                param1 = str(template.get(1).value).strip()
                # Skip if param1 is "image" or looks like a file name
                if param1.lower() not in ['image', 'un'] and not param1.endswith('.svg'):
                    flag_country = param1
                    selected_node = template
                    break

    # If no valid flag country, try to extract from wikilinks
    if not flag_country:
        for link in wikicode.ifilter_wikilinks():
            link_title = str(link.title).strip()
            # Skip File: and Image: links
            if not link_title.startswith(('File:', 'Image:')):
                # Use link text if available, otherwise title
                flag_country = str(link.text).strip() if link.text else link_title
                selected_node = link
                break

    if flag_country:
        # We have a country from flag or link - check if there's additional text/links after it
        # Remove the first template/link and see what's left
        # Remove exactly the node that supplied flag_country; footnote templates
        # (efn, sort, ...) are dropped by clean() below and never count as area.
        remaining = cell_text.replace(str(selected_node), '', 1)
        # Flag templates skipped as country sources (e.g. {{flagicon image|X.svg}})
        # are decoration, not area text.
        for template in wikicode.ifilter_templates():
            if template is not selected_node and _is_decorative_flag(template):
                remaining = remaining.replace(str(template), '', 1)
        remaining = remaining.strip()

        if remaining:
            # Clean the remaining text to get the area
            area_cleaned = clean.clean(remaining, warnings=warnings).strip()
            # Remove leading punctuation like - or –
            area_cleaned = re.sub(r'^[-–\s]+', '', area_cleaned).strip()
            if area_cleaned:
                # {{flagicon|US}} [[United States Minor Outlying Islands]]: the flag
                # param is a bare country code (the flag of the sovereign), and the
                # text is the actual destination - not an area of that country.
                if re.fullmatch(r'[A-Z]{2}', flag_country):
                    return area_cleaned, None
                return flag_country, area_cleaned

        # No area, just the country
        return flag_country, None

    # No flag/link found - fall back to cleaning the whole thing
    cleaned = clean.clean(cell_text, warnings=warnings)

    # Check for area suffix (after - or –)
    if ' - ' in cleaned or ' – ' in cleaned:
        parts = re.split(r'\s+[-–]\s+', cleaned, maxsplit=1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()

    return cleaned.strip(), None


def _find_tables(text: str) -> list[str]:
    """Return top-level wikitables in text.

    Tables open with ``{|`` and close with ``|}`` at the start of a line; nesting is
    depth-counted so inner tables and ``|}`` inside templates (``{{Timatic|DE|}}``)
    do not end the outer table. An unterminated table is dropped.
    """
    tables: list[str] = []
    depth = 0
    start = 0
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith('{|'):
            if depth == 0:
                start = pos + (len(line) - len(stripped))
            depth += 1
        elif stripped.startswith('|}') and depth > 0:
            depth -= 1
            if depth == 0:
                end = pos + (len(line) - len(stripped)) + 2
                tables.append(text[start:end])
        pos += len(line)
    return tables


_HEADER_WORDS = frozenset({
    'country', 'destination', 'visa', 'requirement', 'requirements', 'stay', 'duration',
    'notes', 'note', 'details', 'passport', 'regular', 'special', 'service',
    'diplomatic', 'area', 'territory', 'region', 'entry', 'allowed', 'visitor',
    'or', 'and', 'of', 'the', 'for', 'to', 'maximum', 'length', 'days', 'type', 'name',
    'ordinary', 'official', 'holders', 'other', 'permitted', 'policy', 'status',
})


def _is_header_row(row: dict[str, str]) -> bool:
    """Check if a row looks like a header row (contains column names, not data).

    Args:
        row: Row dict from table parser

    Returns:
        True if this looks like a header row
    """
    if '_group_label' in row:
        return False

    # A header cell is plain header text. Flags, templates and wikilinks to other
    # articles mean a destination (e.g. [[British Indian Ocean Territory]]).
    first_cell = row.get('0', '')
    text = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<[^>]+>', '', first_cell, flags=re.DOTALL)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r'\1', text)  # [[a|b]] -> b
    text = text.replace("'", '').lower()
    if '{{' in text or '[' in text or 'flag' in text:
        return False
    text = re.sub(r'\(.*?\)', ' ', text)
    words = re.findall(r'[a-z]+', text)
    if not words:
        return False
    return all(w in _HEADER_WORDS for w in words)


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

    # Collect header rows and data rows
    # Multiple header rows can exist (e.g., Northern Cyprus has 2 header rows)
    headers = None
    data_rows = []

    for row in rows:
        if '_group_label' in row:
            # Skip group labels
            continue
        # The first row is always a header (as before). Further header rows are only
        # recognised directly after it: once data starts, a row can never replace the
        # headers, however its first cell reads (e.g. "Tibet Autonomous Region").
        if headers is None or (not data_rows and _is_header_row(row)):
            # Use the last leading header row as the column definitions
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

        # Check if this name should be ignored (e.g., "United Nations")
        if countries.should_ignore(dest_name):
            continue

        # Check if this is an area mapping (e.g., "Canary Islands" -> ES + area="Canary Islands")
        area_lookup = countries.lookup_area(dest_name)
        if area_lookup:
            dest_code, area = area_lookup
        else:
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

        # CRITICAL: In territory sections, if canonical name differs from destination name,
        # set area to destination name to distinguish from main-table rows
        # (e.g., "Clipperton Island" -> FR but should be FR+"Clipperton Island")
        if is_territory_or_restricted and not area:
            canonical_name = countries.get_canonical_name(dest_code)
            if canonical_name and countries.normalize_name(canonical_name) != countries.normalize_name(dest_name):
                area = dest_name

        # Extract status BEFORE dedup check so we can compare statuses
        if status_in_stay:
            status_text = row.get(roles['stay'], '')
        else:
            status_text = row.get(roles.get('status', ''), '')

        status_cleaned = clean.clean(status_text, transclusions, result.warnings).strip()

        if not status_cleaned:
            # No status - skip this row with warning
            result.warnings.append(f"Skipping row with no status: {dest_name} in '{section_name}'")
            continue

        # In German-style tables (status_in_stay), check if the "status" is actually just a duration
        # If it parses as pure duration with no text, skip it since the real status is ambiguous
        if status_in_stay:
            test_days, test_note = stay.parse_stay(status_cleaned)
            if test_days and not test_note:
                # This is just a duration (e.g., "4 days"), not a status
                result.warnings.append(f"Skipping row with duration instead of status: {dest_name} in '{section_name}' (found '{status_cleaned}')")
                continue

        primary_status, alternatives = status.parse_status(status_cleaned)

        # Check for duplicate (destination, area) key AFTER status extraction
        # so we can compare statuses and keep the more specific row if they differ
        key = (dest_code, area)
        if key in result._seen_keys:
            prev_idx, prev_section, prev_status, prev_is_territory = result._seen_keys[key]

            if prev_status != primary_status:
                # Statuses differ - keep the more specific (territory) row
                if is_territory_or_restricted and not prev_is_territory and area is None:
                    # Whole-country row vs. a partial restriction (e.g. Baikonur): the
                    # territory row must not displace the whole-country answer. Keep both.
                    result.warnings.append(
                        f"SPLITTING {dest_code}: whole-country {prev_status} in '{prev_section}' kept, "
                        f"{primary_status} row in '{section_name}' stored as area 'Restricted areas'"
                    )
                    area = 'Restricted areas'
                    key = (dest_code, area)
                    if key in result._seen_keys:
                        result.warnings.append(
                            f"Duplicate key {dest_code}+{area!r}: dropped row from '{section_name}'"
                        )
                        continue
                    replace_idx = None
                elif is_territory_or_restricted and not prev_is_territory:
                    # Current row is territory, previous was main - replace
                    result.warnings.append(
                        f"REPLACING {dest_code}+{area!r}: statuses differ ({prev_status} in '{prev_section}' vs {primary_status} in '{section_name}'), keeping territory row"
                    )
                    # We'll replace the old record after building this one
                    replace_idx = prev_idx
                elif not is_territory_or_restricted and prev_is_territory:
                    # Current is main, previous was territory - keep previous
                    result.warnings.append(
                        f"KEEPING territory row for {dest_code}+{area!r}: statuses differ ({prev_status} in '{prev_section}' vs {primary_status} in '{section_name}')"
                    )
                    continue
                else:
                    # Both same type but different statuses - keep first and warn
                    result.warnings.append(
                        f"CONFLICT: {dest_code}+{area!r} has different statuses: {prev_status} in '{prev_section}' vs {primary_status} in '{section_name}', keeping first"
                    )
                    continue
            else:
                # Same status - drop duplicate
                result.warnings.append(
                    f"Duplicate key {dest_code}+{area!r}: first in '{prev_section}', dropped from '{section_name}'"
                )
                continue
        else:
            replace_idx = None

        # Track unmapped statuses (only if not explicitly mapped in STATUS_MAP)
        # This excludes deliberately-special mappings like "Visa Issuance Suspended"
        if primary_status == 'special':
            normalized = status.normalize_status(status_cleaned)
            if normalized not in status.STATUS_MAP:
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

        # Either replace existing record (if replace_idx is set) or append new
        if replace_idx is not None:
            result.records[replace_idx] = record
            # Update seen_keys with new record info
            result._seen_keys[key] = (replace_idx, section_name, primary_status, is_territory_or_restricted)
        else:
            # New record - append and track
            record_idx = len(result.records)
            result.records.append(record)
            result._seen_keys[key] = (record_idx, section_name, primary_status, is_territory_or_restricted)


def _get_section_direct_content(section: dict, all_sections: list[dict], lines: list[str]) -> str:
    """Get the direct content of a section, excluding child sections.

    Args:
        section: Section dict with start_line, end_line, level
        all_sections: List of all sections
        lines: All lines of the wikitext

    Returns:
        Text content of this section only, without child sections
    """
    # Find immediate children (next level down that start within this section)
    children_start_lines = []
    for other in all_sections:
        if (other['start_line'] > section['start_line'] and
            other['start_line'] < section['end_line'] and
            other['level'] == section['level'] + 1):
            children_start_lines.append(other['start_line'])

    if not children_start_lines:
        # No children, return full section
        return '\n'.join(lines[section['start_line']:section['end_line']])

    # Return content up to first child
    return '\n'.join(lines[section['start_line']:children_start_lines[0]])


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

    # Extract section hierarchy
    sections = _extract_section_hierarchy(wikitext)
    lines = wikitext.split('\n')

    # Find the main "Visa requirements" section (level 2 or 3, exact or containing match)
    # Skip "map" sections which typically just contain images
    # Try multiple sections until we find one with tables
    main_section = None
    for section in sections:
        heading_normalized = _normalize_heading(section['heading'])
        # Accept level 2 or 3 sections that contain "visa requirements" but not "map"
        if (section['level'] in (2, 3) and
                'visa requirements' in heading_normalized and
                'map' not in heading_normalized):
            # Check if this section has tables in its direct content
            direct_content = _get_section_direct_content(section, sections, lines)
            if _find_tables(direct_content):
                main_section = section
                break

    # Parse main table (direct content of main section only, not descendants)
    if main_section:
        main_direct_content = _get_section_direct_content(main_section, sections, lines)

        # Extract tables from main section's direct content
        for table_text in _find_tables(main_direct_content):
            _parse_table_rows(
                table_text, passport, 'Visa requirements',
                is_territory_or_restricted=False,
                transclusions=transclusions,
                source_url=source_url,
                source_revision=source_revision,
                result=result
            )

    # Find all territory sections
    if main_section:
        territory_sections = _find_all_territory_sections(
            sections, main_section['start_line']
        )

        # Parse tables from each territory section
        for territory_section in territory_sections:
            # Direct content only: child sections are visited on their own
            direct = _get_section_direct_content(territory_section, sections, lines)
            for table_text in _find_tables(direct):
                _parse_table_rows(
                    table_text, passport, territory_section['heading'],
                    is_territory_or_restricted=True,
                    transclusions=transclusions,
                    source_url=source_url,
                    source_revision=source_revision,
                    result=result
                )

    # Deduplicate warnings
    result.warnings = list(dict.fromkeys(result.warnings))

    return result
