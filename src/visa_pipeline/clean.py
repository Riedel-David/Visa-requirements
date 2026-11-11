"""Clean wikitext: remove refs, resolve links, unwrap templates, normalize whitespace."""
import re

import mwparserfromhell


# Colour templates that wrap status text
COLOUR_TEMPLATES = {
    'yes', 'yes2', 'no', 'no2', 'free', 'optional', 'yes-no',
    'black', 'n/a', 'partial', 'cmain', 'crecurring', 'na', 'usually',
}

# Flag templates that render country names
FLAG_TEMPLATES = {'flag', 'flagu', 'flagcountry', 'flagicon'}

# Templates to drop entirely
DROP_TEMPLATES = {
    'cite', 'timatic', 'cn', 'citation-needed', 'citation needed',
    'current event inline', 'efn', 'refn', 'note',
}


def clean(text: str, transclusions: dict[str, str] | None = None, warnings: list[str] | None = None) -> str:
    """Clean wikitext to plain text.

    Args:
        text: Raw wikitext
        transclusions: Dict from transclusions.parse_template() for resolving {{#section-h::...}}
        warnings: List to append template warnings to (mutated)

    Returns:
        Cleaned plain text
    """
    if warnings is None:
        warnings = []

    # Fix malformed Timatic templates before parsing (trailing pipe without value: |})
    text = re.sub(r'{{[Tt]imatic\|([^}]*)\|}}', r'{{Timatic|\1}}', text)

    wikicode = mwparserfromhell.parse(text)

    # Remove all <ref> tags
    for tag in wikicode.ifilter_tags():
        if tag.tag.lower() in ('ref', 'sup'):
            wikicode.remove(tag)

    # Process templates - collect replacements first to avoid iterator invalidation
    replacements = []
    removals = []

    for template in wikicode.ifilter_templates():
        name = template.name.strip().lower().replace('_', ' ')

        # Drop maintenance templates
        if any(drop in name for drop in DROP_TEMPLATES):
            removals.append(template)
            continue

        # Handle {{sort|key|text}}
        if name == 'sort':
            if template.has(2):
                # Recursively clean the display text in case it contains more templates
                display_text = str(template.get(2).value).strip()
                cleaned_text = clean(display_text, transclusions, warnings)
                replacements.append((template, cleaned_text))
            elif template.has(1):
                # {{sort|eVisa}}: a single argument is the text itself
                replacements.append((template, clean(str(template.get(1).value).strip(), transclusions, warnings)))
            else:
                removals.append(template)
            continue

        # Unwrap colour templates to their text argument
        if name in COLOUR_TEMPLATES:
            # First positional arg is the text (may be arg 1 or 2 depending on template)
            text_content = None
            if template.has(1):
                arg1 = str(template.get(1).value).strip()
                # Check if arg1 is a style attribute
                if '=' not in arg1 or not arg1.startswith('style'):
                    text_content = arg1
                elif template.has(2):
                    text_content = str(template.get(2).value).strip()
            if text_content:
                # Recursively clean in case the content contains nested templates
                cleaned_content = clean(text_content, transclusions, warnings)
                replacements.append((template, cleaned_content))
            else:
                removals.append(template)
            continue

        # Flag templates -> country name
        if any(flag in name for flag in FLAG_TEMPLATES):
            # Extract country name from first positional arg or name= param
            country = None
            if template.has('name'):
                country = str(template.get('name').value).strip()
            elif template.has(1):
                country = str(template.get(1).value).strip()

            if country:
                replacements.append((template, country))
            else:
                # flagicon with no visible text - keep the country code anyway
                if template.has(1):
                    replacements.append((template, str(template.get(1).value).strip()))
                else:
                    removals.append(template)
            continue

        # Handle {{#section-h::Template:Transcluded sections for the visa articles|Heading}}
        # The heading is the first positional parameter (position 1)
        if '#section-h' in name or name.startswith('#'):
            if transclusions and template.has(1):
                heading = str(template.get(1).value).strip()
                if heading in transclusions:
                    # Recursively clean the transcluded content
                    transcluded = transclusions[heading]
                    cleaned_transcluded = clean(transcluded, transclusions, warnings)
                    replacements.append((template, cleaned_transcluded))
                else:
                    removals.append(template)
            else:
                removals.append(template)
            continue

        # Unknown template - drop and warn
        template_name = str(template.name).strip()
        if template_name and template_name not in warnings:
            warnings.append(template_name)
        removals.append(template)

    # Apply all replacements
    for old, new in replacements:
        try:
            wikicode.replace(old, new)
        except ValueError:
            # Template already removed or replaced
            pass

    # Apply all removals
    for template in removals:
        try:
            wikicode.remove(template)
        except ValueError:
            # Template already removed
            pass

    # Resolve wikilinks: [[A|B]] -> B, [[A]] -> A
    # Skip File: and Image: links entirely
    for link in wikicode.ifilter_wikilinks():
        title_str = str(link.title).strip()
        if title_str.startswith(('File:', 'Image:')):
            # Remove file/image links entirely
            wikicode.remove(link)
        elif link.text:
            wikicode.replace(link, link.text)
        else:
            wikicode.replace(link, link.title)

    # Convert to string
    result = str(wikicode)

    # Remove HTML comments
    result = re.sub(r'<!--.*?-->', '', result, flags=re.DOTALL)

    # Remove HTML tags, but convert <br> to newline first
    result = re.sub(r'<br\s*/?>', '\n', result, flags=re.IGNORECASE)
    result = re.sub(r'<[^>]+>', '', result)

    # Normalize whitespace
    result = re.sub(r'\n\s*\n+', '\n', result)  # Multiple newlines to single
    result = re.sub(r'[ \t]+', ' ', result)  # Multiple spaces to single
    result = result.strip()

    return result


# File-image debris left in area text when a flag/coat-of-arms image link is flattened.
_FILE_DEBRIS = re.compile(r'\S*\.(?:png|jpe?g|svg|gif)\b|\bCoats?_of_arms_of_\S*', re.IGNORECASE)
# Genuine reduplicated place names that the duplicate-word collapse must not touch.
_REDUPLICATED_NAMES = {'Bora Bora', 'Pago Pago', 'Wagga Wagga', 'Walla Walla', 'Hua Hua', 'Ban Ban'}
_DOUBLED = re.compile(r'\b(\w[\w\'’.-]*(?: \w[\w\'’.-]*)*?) \1\b')
_EDGE_PUNCT = ' \t\n,;:&-–—'


def _tidy_ws(text: str) -> str:
    """Collapse runs of spaces and strip each line; keep line breaks (they separate list items)."""
    return '\n'.join(' '.join(line.split()) for line in text.split('\n') if line.strip())


def _unwrap_parens(text: str) -> str:
    """Strip one pair of parentheses that wraps the whole string."""
    if text.startswith('(') and text.endswith(')'):
        depth = 0
        for i, ch in enumerate(text):
            depth += (ch == '(') - (ch == ')')
            if depth == 0 and i < len(text) - 1:
                return text
        return text[1:-1]
    return text


def clean_area(text: str | None, country: str | None = None) -> str | None:
    """Tidy area text taken from a destination cell; None if nothing is left.

    Strips surrounding parentheses, whitespace, &nbsp; and stray punctuation, removes
    file-image debris ("X.png", "Coats_of_arms_of_..."), collapses a word repeated by
    flag-name + link-text ("Sabah Sabah" -> "Sabah"), and drops a leading "<country>:".
    A parenthetical that is only a country-name qualifier ("(People's Republic of)")
    is not an area and yields None.
    """
    if not text:
        return None
    text = text.replace('&nbsp;', ' ').replace('\xa0', ' ')
    text = _FILE_DEBRIS.sub(' ', text)
    text = _tidy_ws(text)
    for _ in range(5):  # peel alternating parens / punctuation
        before = text
        text = text.strip(_EDGE_PUNCT)
        if re.fullmatch(r"\(\s*People['’]s Republic of\s*\)", text, re.IGNORECASE):
            return None
        text = _unwrap_parens(text)
        if country and text.lower().startswith(country.lower() + ':'):
            text = text[len(country) + 1:]
        if text == before:
            break
    text = _DOUBLED.sub(lambda m: m.group(0) if m.group(0) in _REDUPLICATED_NAMES else m.group(1), text)
    text = _tidy_ws(text).strip(_EDGE_PUNCT)
    return text or None
