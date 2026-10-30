"""Parse allowed stay duration from cleaned text to days.

Examples:
- "90 days" → (90, None)
- "3 months" → (90, None)
- "1 year" → (365, None)
- "30 days within 180" → (30, "within 180")
- "90 days in any 180-day period" → (90, "in any 180-day period")
- "Unlimited" → (None, "Unlimited")
- "Freedom of movement" → (None, "Freedom of movement")
- "14–30 days" → (None, "14–30 days")
- "" → (None, None)
"""
import re


def parse_stay(text: str) -> tuple[int | None, str | None]:
    """Parse stay duration into (days, extra_note).

    Args:
        text: Cleaned stay text from the table

    Returns:
        (days, extra_note) where:
        - days is an integer if a single duration can be extracted
        - extra_note is any additional context (or the full text if ambiguous)
    """
    if not text or not text.strip():
        return None, None

    text = text.strip()

    # Unlimited / indefinite / freedom of movement
    if re.search(r'\b(unlimited|indefinite|freedom of movement)\b', text, re.IGNORECASE):
        return None, text

    # Ranges like "14–30 days" or "1-3 months"
    if re.search(r'\d+\s*[–-]\s*\d+', text):
        return None, text

    # Multiple values separated by "or"
    if ' or ' in text.lower():
        return None, text

    # Extract days
    days_match = re.search(r'(\d+)\s*days?', text, re.IGNORECASE)
    if days_match:
        days = int(days_match.group(1))
        # Everything after the number is context ("within 180", "in any 180-day period")
        remainder = text[days_match.end():].strip()
        return days, remainder or None

    # Extract months (convert to days: month * 30, except 12 months = 365)
    months_match = re.search(r'(\d+)\s*months?', text, re.IGNORECASE)
    if months_match:
        months = int(months_match.group(1))
        if months == 12:
            days = 365
        else:
            days = months * 30
        remainder = text[months_match.end():].strip()
        extra = remainder if remainder else None
        return days, extra

    # Extract years
    years_match = re.search(r'(\d+)\s*years?', text, re.IGNORECASE)
    if years_match:
        years = int(years_match.group(1))
        days = years * 365
        remainder = text[years_match.end():].strip()
        extra = remainder if remainder else None
        return days, extra

    # No clear duration found - return as note
    return None, text
