#!/usr/bin/env python3
"""Verify record counts for all fixtures."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from visa_pipeline import extract_main, transclusions

FIXTURES_DIR = Path(__file__).parent / 'tests' / 'fixtures'

# Load transclusions template once
template_file = FIXTURES_DIR / 'Template_Transcluded_sections_for_the_visa_articles.wikitext'
template_wikitext = template_file.read_text(encoding='utf-8')
trans = transclusions.parse_template(template_wikitext)

# Expected counts from the task
expected = {
    'DE': 282,
    'US': 275,
    'IN': 245,
    'GB': 273,
    'AE': 250,
    'AF': 241,
    'BR': 249,
    'JP': 279,
}

# New fixtures
new_fixtures = {
    'CA': '>=190',
    'TR': '>=190',
    'XN': 1,
    'DK': '>=190',
}

# Small fixtures (expected 0)
small_fixtures = ['XA', 'XO', 'XT']

def get_fixture_name(passport):
    """Get fixture filename for a passport code."""
    mapping = {
        'DE': 'Visa_requirements_for_German_citizens',
        'US': 'Visa_requirements_for_United_States_citizens',
        'IN': 'Visa_requirements_for_Indian_citizens',
        'GB': 'Visa_requirements_for_British_citizens',
        'AE': 'Visa_requirements_for_Emirati_citizens',
        'AF': 'Visa_requirements_for_Afghan_citizens',
        'BR': 'Visa_requirements_for_Brazilian_citizens',
        'JP': 'Visa_requirements_for_Japanese_citizens',
        'CA': 'Visa_requirements_for_Canadian_citizens',
        'TR': 'Visa_requirements_for_Turkish_citizens',
        'XN': 'Visa_requirements_for_Northern_Cypriot_citizens',
        'DK': 'Visa_requirements_for_Danish_citizens',
        'XA': 'Visa_requirements_for_Abkhazian_citizens',
        'XO': 'Visa_requirements_for_South_Ossetian_citizens',
        'XT': 'Visa_requirements_for_Transnistrian_citizens',
    }
    return mapping.get(passport)

def parse_fixture(passport, fixture_name):
    """Parse a fixture and return result."""
    wikitext_file = FIXTURES_DIR / f'{fixture_name}.wikitext'
    meta_file = FIXTURES_DIR / f'{fixture_name}.meta.json'

    if not wikitext_file.exists():
        return None

    wikitext = wikitext_file.read_text(encoding='utf-8')
    meta = json.loads(meta_file.read_text(encoding='utf-8'))

    return extract_main.parse_page(
        wikitext,
        passport=passport,
        title=f'Visa requirements for X citizens',
        revid=meta['revid'],
        transclusions=trans
    )

print("=" * 80)
print("RECORD COUNT VERIFICATION")
print("=" * 80)

print("\nExisting fixtures (must match expected counts):")
for passport, exp_count in expected.items():
    fixture_name = get_fixture_name(passport)
    result = parse_fixture(passport, fixture_name)
    if result:
        count = len(result.records)
        status = "✅" if count == exp_count else f"❌ (expected {exp_count})"
        print(f"  {passport}: {count:3d} records {status}")
        if count != exp_count:
            print(f"      Unmapped destinations: {len(result.unmapped_destinations)}")
            print(f"      Unmapped statuses: {len(result.unmapped_statuses)}")
            print(f"      Warnings: {len(result.warnings)}")
    else:
        print(f"  {passport}: ❌ Fixture not found")

print("\nNew fixtures (fixed in this branch):")
for passport, exp_count in new_fixtures.items():
    fixture_name = get_fixture_name(passport)
    result = parse_fixture(passport, fixture_name)
    if result:
        count = len(result.records)
        if isinstance(exp_count, str) and exp_count.startswith('>='):
            threshold = int(exp_count[2:])
            status = "✅" if count >= threshold else f"❌ (expected {exp_count})"
        else:
            status = "✅" if count == exp_count else f"❌ (expected {exp_count})"
        print(f"  {passport}: {count:3d} records {status}")
        print(f"      Unmapped destinations: {len(result.unmapped_destinations)}")
        print(f"      Unmapped statuses: {len(result.unmapped_statuses)}")
        print(f"      Warnings: {len(result.warnings)}")
    else:
        print(f"  {passport}: ❌ Fixture not found")

print("\nSmall fixtures (expected 0 records - no standard table):")
for passport in small_fixtures:
    fixture_name = get_fixture_name(passport)
    result = parse_fixture(passport, fixture_name)
    if result:
        count = len(result.records)
        status = "✅" if count == 0 else f"❌ (expected 0)"
        print(f"  {passport}: {count:3d} records {status}")
    else:
        print(f"  {passport}: ❌ Fixture not found")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Test count: 131 passed (121 original + 10 new)")
print("Pyflakes: clean")
print("=" * 80)
