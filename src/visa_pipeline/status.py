"""Map visa status text to enum values.

This module provides the canonical mapping from cleaned, normalized status text
(as it appears in Wikipedia tables after template unwrapping) to the visa status enum.

Status enum order (least to most restrictive):
    visa_free < visa_on_arrival < eta < evisa < visa_required < permit_required < admission_refused

special sits outside this order and is used for unmapped or unusual statuses.

For combined statuses like "eVisa / Visa on arrival", the parser splits on "/" and " or ",
takes the least restrictive as the main status, and puts others in alternative_statuses.

## Mapping principles

1. Map on the cleaned text content, not the template name ({{free|Visa required}} exists)
2. Normalize to lowercase and strip whitespace before lookup
3. Never guess - unmapped text becomes "special" with a warning
4. Order matters - check more specific patterns before general ones

## Examples from fixtures

- "Visa not required" → visa_free
- "Freedom of movement" → visa_free
- "eVisa" → evisa
- "Visa on arrival" → visa_on_arrival
- "Electronic Travel Authorisation" → eta
- "Visa required" → visa_required
- "eVisa / Visa on arrival" → split, least restrictive wins
- "Admission refused" → admission_refused
- "Special permit required" → permit_required
"""

# Ordered mapping table: status text -> enum value
# Order: check more specific patterns first
STATUS_MAP = {
    # Visa-free entry
    'visa not required': 'visa_free',
    'visa not required (conditional)': 'visa_free',
    'visa-free': 'visa_free',
    'visa free': 'visa_free',
    'no visa required': 'visa_free',
    'freedom of movement': 'visa_free',
    'visa not required (ease)': 'visa_free',
    'id card valid': 'visa_free',
    'id card': 'visa_free',
    'visa exemption': 'visa_free',
    'visa waiver': 'visa_free',

    # Electronic Travel Authorization (ETA)
    'electronic travel authorisation': 'eta',
    'electronic travel authorization': 'eta',
    'electronic travel authority': 'eta',
    'eta': 'eta',
    'esta': 'eta',
    'evisitor': 'eta',
    'eta-il': 'eta',
    'k-eta': 'eta',
    'electronic system for travel authorization': 'eta',
    'electronic system for travel authorisation': 'eta',

    # eVisa (applied for online before travel)
    'evisa': 'evisa',
    'e-visa': 'evisa',
    'online visa': 'evisa',
    'electronic visa': 'evisa',
    'visa online': 'evisa',
    'e-tourist visa': 'evisa',

    # Visa on arrival (obtained at border)
    'visa on arrival': 'visa_on_arrival',
    'visa upon arrival': 'visa_on_arrival',
    'voa': 'visa_on_arrival',
    'free visa on arrival': 'visa_on_arrival',
    'tourist card on arrival': 'visa_on_arrival',
    'entry permit on arrival': 'visa_on_arrival',
    'landing visa': 'visa_on_arrival',
    'visitor card on arrival': 'visa_on_arrival',
    # e-VOA: applied online but obtained at arrival - treating as visa_on_arrival
    # since the key difference is that approval/payment happens at the border
    'e-voa': 'visa_on_arrival',
    'electronic visa on arrival': 'visa_on_arrival',

    # Visa required (must obtain in advance)
    'visa required': 'visa_required',
    'visa necessary': 'visa_required',
    'online visa required': 'visa_required',
    'pre-arranged visa': 'visa_required',

    # Special permits (more restrictive than regular visa)
    'special permit required': 'permit_required',
    'permit required': 'permit_required',
    'travel permit required': 'permit_required',
    'special permission required': 'permit_required',
    'permission required': 'permit_required',
    'restricted area': 'permit_required',
    'ttp required': 'permit_required',
    'travel pass required': 'permit_required',
    'entry permit required': 'permit_required',

    # Admission refused
    'admission refused': 'admission_refused',
    'entry denied': 'admission_refused',
    'no admission': 'admission_refused',
    'travel banned': 'admission_refused',
    'travel not permitted': 'admission_refused',

    # Special cases that map to specific values
    'visa issuance suspended': 'special',
    'undefined': 'special',
    'visa regime undefined': 'special',
}


def normalize_status(text: str) -> str:
    """Normalize status text for lookup: lowercase, strip, compress whitespace."""
    return ' '.join(text.lower().split())


def parse_status(text: str) -> tuple[str, list[str]]:
    """Parse a visa status string into (primary_status, alternative_statuses).

    Handles combined statuses like "eVisa / Visa on arrival" by splitting and
    choosing the least restrictive option as primary.

    Args:
        text: Cleaned status text from the table

    Returns:
        (status_enum, list_of_alternative_status_enums)
        If unmapped, returns ('special', [])
    """
    # Split on "/" or " or "
    parts = [p.strip() for p in text.replace(' or ', '/').split('/')]

    if len(parts) == 1:
        # Single status
        normalized = normalize_status(parts[0])
        return STATUS_MAP.get(normalized, 'special'), []

    # Multiple statuses - map each and pick the least restrictive
    # Status order (least to most restrictive):
    order = ['visa_free', 'visa_on_arrival', 'eta', 'evisa', 'visa_required',
             'permit_required', 'admission_refused', 'special']

    mapped = []
    for part in parts:
        normalized = normalize_status(part)
        status = STATUS_MAP.get(normalized, 'special')
        if status not in mapped:
            mapped.append(status)

    if not mapped:
        return 'special', []

    # Sort by restrictiveness and pick the least restrictive
    mapped_sorted = sorted(mapped, key=lambda s: order.index(s))
    primary = mapped_sorted[0]
    alternatives = mapped_sorted[1:]

    return primary, alternatives
