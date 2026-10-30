"""Discover and map visa requirement pages."""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .api import WikiClient
from .demonyms import demonym_to_iso2


# Pattern for visa requirement page titles
VISA_REQ_PATTERN = re.compile(r"^Visa requirements for (.+) citizens$")


def load_overrides(overrides_path: Path) -> dict[str, str | None]:
    """
    Load passport overrides from JSON file.

    Args:
        overrides_path: Path to overrides/passports.json

    Returns:
        Dict mapping exact title to ISO2 or null

    Raises:
        FileNotFoundError: if the file is missing (never silently empty)
    """
    with open(overrides_path) as f:
        return json.load(f)


def discover_pages(
    client: WikiClient,
    overrides: dict[str, str | None]
) -> list[dict[str, Any]]:
    """
    Discover visa requirement pages from category.

    Args:
        client: WikiClient instance
        overrides: Title -> ISO2 override mapping

    Returns:
        List of page records: {title, passport|None, reason}
    """
    # Get direct members (articles)
    pages = client.category_members("Visa requirements by nationality", namespace=0)

    # Also check for subcategories
    subcats = client.category_members("Visa requirements by nationality", namespace=14)

    # If there are subcategories, recursively get their members (only one level)
    for subcat in subcats:
        pages.extend(client.category_members(subcat, namespace=0))

    # Remove duplicates
    pages = list(set(pages))

    results = []
    seen_passports = {}

    for title in sorted(pages):
        # Check override first
        if title in overrides:
            override_code = overrides[title]
            if override_code is None:
                # Deliberately excluded
                results.append({
                    "title": title,
                    "passport": None,
                    "reason": "excluded by override"
                })
                continue
            else:
                # Override mapping
                if override_code in seen_passports:
                    results.append({
                        "title": title,
                        "passport": None,
                        "reason": f"duplicate passport code {override_code} (already mapped to {seen_passports[override_code]})"
                    })
                else:
                    seen_passports[override_code] = title
                    results.append({
                        "title": title,
                        "passport": override_code,
                        "reason": "override"
                    })
                continue

        # Try to match pattern
        match = VISA_REQ_PATTERN.match(title)
        if not match:
            results.append({
                "title": title,
                "passport": None,
                "reason": "title does not match pattern"
            })
            continue

        demonym = match.group(1)
        iso2 = demonym_to_iso2(demonym)

        if iso2 is None:
            results.append({
                "title": title,
                "passport": None,
                "reason": f"unmapped demonym: {demonym}"
            })
            continue

        # Check for duplicates
        if iso2 in seen_passports:
            results.append({
                "title": title,
                "passport": None,
                "reason": f"duplicate passport code {iso2} (already mapped to {seen_passports[iso2]})"
            })
            continue

        seen_passports[iso2] = title
        results.append({
            "title": title,
            "passport": iso2,
            "reason": "demonym mapping"
        })

    return results


def load_pages_cache(state_dir: Path) -> dict[str, Any] | None:
    """
    Load cached page discovery results.

    Args:
        state_dir: State directory path

    Returns:
        Cached data or None if not found/too old
    """
    cache_file = state_dir / "pages.json"
    if not cache_file.exists():
        return None

    with open(cache_file) as f:
        data = json.load(f)

    # Check age (refresh if older than 7 days)
    fetched_at = datetime.fromisoformat(data["fetched_at"])
    age_days = (datetime.now(timezone.utc) - fetched_at).days

    if age_days >= 7:
        return None

    return data


def save_pages_cache(state_dir: Path, pages: list[dict[str, Any]]) -> None:
    """
    Save page discovery results to cache.

    Args:
        state_dir: State directory path
        pages: List of page records
    """
    state_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pages": pages
    }

    cache_file = state_dir / "pages.json"
    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_pages(
    client: WikiClient,
    state_dir: Path,
    overrides_path: Path,
    refresh: bool = False
) -> list[dict[str, Any]]:
    """
    Get visa requirement pages (from cache or fresh discovery).

    Args:
        client: WikiClient instance
        state_dir: State directory path
        overrides_path: Path to overrides/passports.json
        refresh: Force refresh even if cache is valid

    Returns:
        List of page records
    """
    # Try cache first
    if not refresh:
        cached = load_pages_cache(state_dir)
        if cached is not None:
            return cached["pages"]

    # Fresh discovery
    overrides = load_overrides(overrides_path)
    pages = discover_pages(client, overrides)
    save_pages_cache(state_dir, pages)

    return pages
