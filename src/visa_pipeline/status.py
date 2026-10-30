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
    'visa not required(conditional)': 'visa_free',
    'not required': 'visa_free',
    'visa-free': 'visa_free',
    'visa free': 'visa_free',
    'visa free with payment': 'visa_free',
    'no visa required': 'visa_free',
    'freedom of movement': 'visa_free',
    'visa not required (ease)': 'visa_free',
    'id card valid': 'visa_free',
    'id card': 'visa_free',
    'visa exemption': 'visa_free',
    'visa waiver': 'visa_free',
    'visa waiver program': 'visa_free',

    # Electronic Travel Authorization (ETA)
    'electronic travel authorisation': 'eta',
    'electronic travel authorization': 'eta',
    'electronic travel authority': 'eta',
    'electronic authorization': 'eta',
    'electronic authorisation': 'eta',
    'authorisation required': 'eta',
    'authorization required': 'eta',
    'authoristion required': 'eta',  # Common typo
    'special authorisation permit': 'eta',
    'special authorization permit': 'eta',
    'pre-registration required': 'eta',
    'eta': 'eta',
    'esta': 'eta',
    'evisitor': 'eta',
    'eta-il': 'eta',
    'k-eta': 'eta',
    'nzeta': 'eta',
    'electronic border system': 'eta',  # Seychelles STTA
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
    "free visitor's permit on arrival": 'visa_on_arrival',
    'visa on arrival (ease)': 'visa_on_arrival',
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
    'access permit required': 'permit_required',
    'travel permit required': 'permit_required',
    'special permission required': 'permit_required',
    'permission required': 'permit_required',
    'restricted area': 'permit_required',
    'ttp required': 'permit_required',
    'travel pass required': 'permit_required',
    'entry permit required': 'permit_required',
    'pap/rap required': 'permit_required',
    'ovir permit required': 'permit_required',
    'oivr permit required': 'permit_required',
    'special authorization required': 'permit_required',
    'special authorisation required': 'permit_required',
    'special access required': 'permit_required',
    'special permits required': 'permit_required',

    # Admission refused
    'admission refused': 'admission_refused',
    'entry denied': 'admission_refused',
    'no admission': 'admission_refused',
    'travel banned': 'admission_refused',
    'travel not permitted': 'admission_refused',

    # Special cases - deliberate 'special' mappings
    # These are mapped to 'special' rather than leaving unmapped so they appear
    # in the final report with context rather than as unknown statuses
    'visa issuance suspended': 'special',  # Temporary suspension, not permanent refusal
    'admission restricted': 'special',  # Restricted but not completely refused
    'travel restricted': 'special',
    'undefined': 'special',
    'visa regime undefined': 'special',
    'organized trips': 'special',  # Only via organized tours

    # Edge cases that should be normalized
    'freedom of movement (european netherlands)': 'visa_free',

    # Compound/complex special cases
    'travel restricted by u.s. government/admission refused for u.s. citizens with foreign nationality': 'special',
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
    # Try exact match first (handles compound acronyms like "PAP/RAP required")
    normalized_full = normalize_status(text)
    if normalized_full in STATUS_MAP:
        return STATUS_MAP[normalized_full], []

    # Split on " / ", " or ", or "/" (without spaces if between longer words)
    # This handles both "eVisa / Visa on arrival" and "eVisa/Visa on arrival"
    # but avoids splitting acronyms like "PAP/RAP"
    parts = []
    if ' / ' in text or ' or ' in text:
        parts = [p.strip() for p in text.replace(' or ', ' / ').split(' / ')]
    elif '/' in text:
        # Try splitting on bare "/" and see if parts are valid
        potential_parts = [p.strip() for p in text.split('/')]
        # Only split if we get multiple reasonable-length parts (> 3 chars to avoid splitting acronyms)
        if len(potential_parts) >= 2 and all(len(p) > 3 for p in potential_parts):
            parts = potential_parts

    if len(parts) <= 1:
        # Single status (or not a valid combined status)
        return 'special', []

    # Multiple statuses - map each and pick the least restrictive
    # Status order (least to most restrictive):
    order = ['visa_free', 'visa_on_arrival', 'eta', 'evisa', 'visa_required',
             'permit_required', 'admission_refused', 'special']

    mapped = []
    for part in parts:
        status = STATUS_MAP.get(normalize_status(part), 'special')
        # One unmapped (or special) part makes the whole cell special, so the
        # caller reports it instead of us guessing from the remaining parts
        if status == 'special':
            return 'special', []
        if status not in mapped:
            mapped.append(status)

    # Least restrictive is primary; the rest keep their order of appearance
    primary = min(mapped, key=order.index)
    alternatives = [s for s in mapped if s != primary]

    return primary, alternatives
