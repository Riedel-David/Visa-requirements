"""Clean wikitext: remove refs, resolve links, unwrap templates, normalize whitespace."""
import re
from typing import Any

import mwparserfromhell


# Colour templates that wrap status text
COLOUR_TEMPLATES = {
    'yes', 'yes2', 'no', 'no2', 'free', 'optional', 'yes-no',
    'black', 'n/a', 'partial', 'cmain', 'crecurring', 'na',
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
                replacements.append((template, str(template.get(2).value).strip()))
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
                replacements.append((template, text_content))
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
        if '#section-h' in name or name.startswith('#'):
            if transclusions and template.has(2):
                heading = str(template.get(2).value).strip()
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
    for link in wikicode.ifilter_wikilinks():
        if link.text:
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
