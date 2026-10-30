"""Parse Template:Transcluded sections for the visa articles into named sections."""
import mwparserfromhell

TEMPLATE_TITLE = "Template:Transcluded sections for the visa articles"


def parse_template(wikitext: str) -> dict[str, str]:
    """Split the transclusion template wikitext into {section heading: section wikitext}.

    The template contains sections like:
    ==Algeria. VOA==
    * Bullet points...

    Returns a dict where keys are the section headings (e.g., "Algeria. VOA")
    and values are the full wikitext content of that section.
    """
    wikicode = mwparserfromhell.parse(wikitext)
    sections = wikicode.get_sections(levels=[2], include_headings=True)

    result = {}
    for section in sections:
        # Skip the first section if it's not a real heading
        section_text = str(section).strip()
        if not section_text or section_text.startswith("This is a technical"):
            continue

        # Extract heading
        lines = section_text.split("\n", 1)
        if not lines[0].startswith("=="):
            continue

        heading = lines[0].strip("= \n")
        content = lines[1].strip() if len(lines) > 1 else ""

        if heading and content:
            result[heading] = content

    return result
