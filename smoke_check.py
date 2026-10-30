#!/usr/bin/env python3
"""Live smoke check: discover pages and fetch revision info."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from visa_pipeline.api import WikiClient
from visa_pipeline.discover import discover_pages, save_pages_cache


def main():
    """Run discovery smoke check."""
    print("=== Live Smoke Check ===")
    print()

    # Initialize client
    client = WikiClient(min_interval=1.0)

    # Load overrides
    overrides_path = Path(__file__).parent / "src" / "visa_pipeline" / "overrides" / "passports.json"
    with open(overrides_path) as f:
        overrides = json.load(f)

    print(f"Loaded {len(overrides)} overrides")
    print()

    # Discover pages
    print("Discovering pages from 'Category:Visa requirements by nationality'...")
    pages = discover_pages(client, overrides)

    # Separate mapped and unmapped
    mapped = [p for p in pages if p["passport"] is not None]
    unmapped = [p for p in pages if p["passport"] is None]

    print(f"Found {len(pages)} pages total")
    print(f"  - {len(mapped)} mapped to passport codes")
    print(f"  - {len(unmapped)} unmapped/excluded")
    print()

    # Show unmapped/excluded
    if unmapped:
        print("Unmapped/excluded pages:")
        for page in unmapped:
            print(f"  - {page['title']}")
            print(f"    Reason: {page['reason']}")
        print()

    # Get revision info for a sample (first 5 mapped pages)
    if mapped:
        sample = mapped[:5]
        titles = [p["title"] for p in sample]
        print(f"Fetching revision info for {len(sample)} sample pages...")
        revisions = client.revisions(titles)
        print(f"Retrieved {len(revisions)} revision records")
        for title in titles:
            if title in revisions:
                print(f"  - {title}: rev {revisions[title]['revid']}")
        print()

    # Save to state/pages.json
    state_dir = Path(__file__).parent / "state"
    save_pages_cache(state_dir, pages)
    print(f"Saved discovery results to {state_dir}/pages.json")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Total pages: {len(pages)}")
    print(f"Mapped: {len(mapped)}")
    print(f"Unmapped/excluded: {len(unmapped)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
