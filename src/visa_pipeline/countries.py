"""Map destination names to ISO 3166-1 alpha-2 codes or user-assigned X-codes.

Uses pycountry for standard lookups, plus hand-written aliases for Wikipedia names
and X-codes for non-ISO entities (Kosovo, Northern Cyprus, etc.) from overrides/destinations.json.
"""
import json
from importlib.resources import files

import pycountry


# Wikipedia-specific aliases not in pycountry
WIKIPEDIA_ALIASES = {
    'ivory coast': 'CI',
    'cape verde': 'CV',
    'east timor': 'TL',
    'republic of the congo': 'CG',
    'congo-brazzaville': 'CG',
    'democratic republic of the congo': 'CD',
    'congo-kinshasa': 'CD',
    'dr congo': 'CD',
    'micronesia': 'FM',
    'macau': 'MO',
    'macao': 'MO',
    'vatican city': 'VA',
    'holy see': 'VA',
    'palestine': 'PS',
    'state of palestine': 'PS',
    'taiwan': 'TW',
    'south korea': 'KR',
    'north korea': 'KP',
    'russia': 'RU',
    'turkey': 'TR',
    'eswatini': 'SZ',
    'são tomé and príncipe': 'ST',
    'sao tome and principe': 'ST',
    'brunei': 'BN',
    'laos': 'LA',
    'syria': 'SY',
    'iran': 'IR',
    'moldova': 'MD',
    'bolivia': 'BO',
    'venezuela': 'VE',
    'tanzania': 'TZ',
    'vietnam': 'VN',
    'åland islands': 'AX',
    'aland islands': 'AX',
    'caribbean netherlands': 'BQ',
    'bonaire': 'BQ',
    'sint eustatius': 'BQ',
    'saba': 'BQ',
    'united states': 'US',
    'united kingdom': 'GB',
    'south ossetia': 'XO',  # User-assigned
    'abkhazia': 'XA',  # User-assigned
    'transnistria': 'XT',  # User-assigned
    'northern cyprus': 'XN',  # From override
    'somaliland': 'XS',  # From override
    'kosovo': 'XK',  # From override
    # British territories
    'saint helena': 'SH',
    'ascension island': 'SH',
    'tristan da cunha': 'SH',
    'gibraltar': 'GI',
    'falkland islands': 'FK',
    'pitcairn islands': 'PN',
    'british antarctic territory': 'AQ',
    # French territories
    'saint martin': 'MF',
    'french southern and antarctic lands': 'TF',
    # Dutch territories
    'sint maarten': 'SX',
    # US territories
    'u.s. virgin islands': 'VI',
    'us virgin islands': 'VI',
    # Other
    'argentine antarctica': 'AQ',
    'kurdish region': 'IQ',  # Iraqi Kurdistan
    'kurdistan region': 'IQ',
    'iraqi kurdistan': 'IQ',
    # Special regions
    'the bahamas': 'BS',
    'bahamas': 'BS',
    'svalbard': 'SJ',
    'crimea': 'UA',  # Disputed, using Ukraine code
    'novorossiya': 'UA',  # Disputed, using Ukraine code
    'clipperton island': 'FR',  # French territory
    'akrotiri and dhekelia': 'GB',  # UK Sovereign Base Areas in Cyprus
    'mount athos': 'GR',  # Greek autonomous region
    'curacao': 'CW',
    'curaçao': 'CW',
    'turkish republic of northern cyprus': 'XN',
    'antartica chilena province': 'AQ',
    'antártica chilena province': 'AQ',
    'chilean antarctic territory': 'AQ',
    'galápagos': 'EC',
    'galapagos': 'EC',
}

# Cache for loaded overrides
_overrides_cache: dict[str, str] | None = None


def _load_overrides() -> dict[str, str]:
    """Load destination overrides from overrides/destinations.json."""
    global _overrides_cache
    if _overrides_cache is not None:
        return _overrides_cache

    try:
        override_file = files('visa_pipeline') / 'overrides' / 'destinations.json'
        content = override_file.read_text(encoding='utf-8')
        data = json.loads(content)
        _overrides_cache = data
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        _overrides_cache = {}
        return {}


def normalize_name(name: str) -> str:
    """Normalize a destination name for lookup: lowercase, strip, compress whitespace."""
    return ' '.join(name.lower().split())


def lookup_country(name: str) -> str | None:
    """Map a destination name to an ISO 3166-1 alpha-2 code or X-code.

    Lookup order:
    1. Overrides from destinations.json
    2. Wikipedia aliases
    3. pycountry by name
    4. pycountry by common_name
    5. pycountry by official_name

    Args:
        name: Destination name from the Wikipedia table

    Returns:
        ISO 3166-1 alpha-2 code, X-code, or None if not found
    """
    normalized = normalize_name(name)

    # Load overrides
    overrides = _load_overrides()

    # Check overrides first
    if normalized in overrides:
        return overrides[normalized]

    # Check Wikipedia aliases
    if normalized in WIKIPEDIA_ALIASES:
        return WIKIPEDIA_ALIASES[normalized]

    # Try pycountry
    try:
        country = pycountry.countries.get(name=name)
        if country:
            return country.alpha_2
    except (KeyError, LookupError):
        pass

    # Try common_name
    try:
        for country in pycountry.countries:
            if hasattr(country, 'common_name') and normalize_name(country.common_name) == normalized:
                return country.alpha_2
    except (KeyError, LookupError, AttributeError):
        pass

    # Try official_name
    try:
        for country in pycountry.countries:
            if hasattr(country, 'official_name') and normalize_name(country.official_name) == normalized:
                return country.alpha_2
    except (KeyError, LookupError, AttributeError):
        pass

    # Not found
    return None
