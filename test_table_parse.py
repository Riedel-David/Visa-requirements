#!/usr/bin/env python3
"""Test table parsing."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from visa_pipeline import table

def test_fixture_table(fixture_name: str, section_name: str):
    fixture_path = Path(__file__).parent / 'tests' / 'fixtures' / f'{fixture_name}.wikitext'
    wikitext = fixture_path.read_text(encoding='utf-8')

    # Find the section
    if section_name.startswith('==='):
        pattern = f'^{re.escape(section_name)}'
    else:
        pattern = f'^{re.escape(section_name)}'

    lines = wikitext.split('\n')
    section_start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            section_start = i
            break

    if not section_start:
        print(f"❌ Section not found: {section_name}")
        return

    # Extract section until next same-level heading
    section_lines = []
    level = len(section_name.split()[0])  # Count '=' chars
    for line in lines[section_start:]:
        if line.startswith('==') and len(line.split()[0]) <= level and line != section_name:
            break
        section_lines.append(line)

    section_text = '\n'.join(section_lines)

    # Find table
    table_matches = list(re.finditer(r'\{\|.*?\|\}', section_text, re.DOTALL))
    if not table_matches:
        print(f"❌ No table found in section {section_name}")
        return

    table_text = table_matches[0].group(0)

    print(f"\n{'='*60}")
    print(f"Testing: {fixture_name} / {section_name}")
    print(f"{'='*60}")

    rows = table.parse_table(table_text)
    print(f"Total rows: {len(rows)}")

    for i, row in enumerate(rows[:10]):
        if '_group_label' in row:
            print(f"  Row {i}: GROUP LABEL: {row['_group_label'][:50]}")
        else:
            # Show first 3 columns
            cols = sorted(row.keys(), key=lambda x: int(x) if x.isdigit() else 999)[:3]
            content = ' | '.join(f"{k}:{row[k][:30]}" for k in cols if k in row)
            print(f"  Row {i}: {content}")

if __name__ == '__main__':
    test_fixture_table('Visa_requirements_for_Canadian_citizens', '===Visa requirements===')
    test_fixture_table('Visa_requirements_for_Northern_Cypriot_citizens', '==Visa requirements==')
