"""Generic wikitable parser: raw table wikitext -> list of row dicts."""
import re
from dataclasses import dataclass


@dataclass
class Cell:
    """A table cell with its content and attributes."""
    content: str
    is_header: bool = False
    rowspan: int = 1
    colspan: int = 1
    attributes: dict[str, str] | None = None


def _mask_nested_content(text: str) -> tuple[str, dict[str, str]]:
    """Mask {{...}}, [[...]], <ref>...</ref>, and <!-- --> to prevent pipe splitting.

    Returns (masked_text, replacements_dict)
    """
    replacements = {}
    counter = [0]

    def make_placeholder():
        counter[0] += 1
        return f"___MASK{counter[0]}___"

    # Mask HTML comments first
    def mask_comments(m):
        placeholder = make_placeholder()
        replacements[placeholder] = m.group(0)
        return placeholder
    text = re.sub(r'<!--.*?-->', mask_comments, text, flags=re.DOTALL)

    # Mask <ref>...</ref> tags
    def mask_refs(m):
        placeholder = make_placeholder()
        replacements[placeholder] = m.group(0)
        return placeholder
    text = re.sub(r'<ref[^>]*>.*?</ref>', mask_refs, text, flags=re.DOTALL)
    text = re.sub(r'<ref[^/>]*\s*/>', mask_refs, text)

    # Mask {{...}} templates (with nesting)
    while True:
        original = text
        def mask_templates(m):
            placeholder = make_placeholder()
            replacements[placeholder] = m.group(0)
            return placeholder
        # Match innermost templates first
        text = re.sub(r'\{\{[^{}]*\}\}', mask_templates, text)
        if text == original:
            break

    # Mask [[...]] links
    def mask_links(m):
        placeholder = make_placeholder()
        replacements[placeholder] = m.group(0)
        return placeholder
    text = re.sub(r'\[\[[^\]]*\]\]', mask_links, text)

    return text, replacements


def _unmask_content(text: str, replacements: dict[str, str]) -> str:
    """Unmask previously masked content."""
    for placeholder, original in replacements.items():
        text = text.replace(placeholder, original)
    return text


def _parse_cell_attributes(attr_text: str) -> tuple[dict[str, str], int]:
    """Parse cell attributes and return (attributes_dict, colspan, rowspan).

    Handles both normal form: `style="..." data-sort-value="4" | content`
    and glued form: `data-sort-value="4" {{template...}}`
    """
    attrs = {}
    colspan = 1
    rowspan = 1

    # Try to find pipe separator first
    if '|' in attr_text:
        # Find the last | that's not inside {{ }} or [[ ]]
        depth_curly = 0
        depth_bracket = 0
        split_pos = -1

        for i, char in enumerate(attr_text):
            if char == '{' and i + 1 < len(attr_text) and attr_text[i + 1] == '{':
                depth_curly += 1
            elif char == '}' and i + 1 < len(attr_text) and attr_text[i + 1] == '}':
                depth_curly -= 1
            elif char == '[' and i + 1 < len(attr_text) and attr_text[i + 1] == '[':
                depth_bracket += 1
            elif char == ']' and i + 1 < len(attr_text) and attr_text[i + 1] == ']':
                depth_bracket -= 1
            elif char == '|' and depth_curly == 0 and depth_bracket == 0:
                split_pos = i

        if split_pos > 0:
            # Parse attributes before |
            attr_part = attr_text[:split_pos].strip()
            for attr_match in re.finditer(r'(\w+(?:-\w+)*)=(["\']?)([^"\']*?)\2(?:\s|$)', attr_part):
                key = attr_match.group(1)
                value = attr_match.group(3)
                attrs[key] = value

                if key == 'colspan':
                    try:
                        colspan = int(value)
                    except ValueError:
                        pass
                elif key == 'rowspan':
                    try:
                        rowspan = int(value)
                    except ValueError:
                        pass

            return attrs, colspan, rowspan

    # No pipe or glued form - check for attribute pattern at start
    # Match: `data-sort-value="123" ` or `style="..." ` etc
    attr_match = re.match(r'^(\w+(?:-\w+)*)=(["\']?)([^"\']*?)\2\s+', attr_text)
    if attr_match:
        key = attr_match.group(1)
        value = attr_match.group(3)
        attrs[key] = value

        if key == 'colspan':
            try:
                colspan = int(value)
            except ValueError:
                pass
        elif key == 'rowspan':
            try:
                rowspan = int(value)
            except ValueError:
                pass

    return attrs, colspan, rowspan


def _split_inline_cells(line: str, delimiter: str) -> list[str]:
    """Split a line on delimiter (|| or !!) while respecting {{ }} and [[ ]] nesting."""
    cells = []
    current = []
    depth_curly = 0
    depth_bracket = 0
    i = 0

    while i < len(line):
        if i + 1 < len(line):
            two_char = line[i:i+2]
            if two_char == '{{':
                depth_curly += 1
                current.append(line[i:i+2])
                i += 2
                continue
            elif two_char == '}}':
                depth_curly -= 1
                current.append(line[i:i+2])
                i += 2
                continue
            elif two_char == '[[':
                depth_bracket += 1
                current.append(line[i:i+2])
                i += 2
                continue
            elif two_char == ']]':
                depth_bracket -= 1
                current.append(line[i:i+2])
                i += 2
                continue
            elif two_char == delimiter and depth_curly == 0 and depth_bracket == 0:
                cells.append(''.join(current))
                current = []
                i += 2
                continue

        current.append(line[i])
        i += 1

    if current:
        cells.append(''.join(current))

    return cells


def parse_table(table_text: str) -> list[dict[str, str]]:
    """Parse a wikitable into a list of row dicts.

    Each row is a dict mapping column indices ("0", "1", etc.) to cell content.
    Group header rows (full-width headers with large colspan) are returned as
    {"_group_label": "heading text"}.

    Args:
        table_text: Raw wikitext of a wikitable (from {| to |})

    Returns:
        List of dicts, one per row. Regular rows have numeric string keys.
        Group headers have a single "_group_label" key.
    """
    # Mask nested content to prevent multi-line templates/refs from breaking table structure
    masked_text, replacements = _mask_nested_content(table_text)

    lines = masked_text.strip().split('\n')
    rows: list[list[Cell]] = []
    current_row: list[Cell] | None = None

    # Track cells that span multiple rows
    rowspan_carry: dict[int, Cell] = {}  # col_idx -> Cell

    for line in lines:
        line = line.strip()

        # Skip table start/end and captions
        if line.startswith('{|') or line == '|}' or line.startswith('|+'):
            continue

        # Row separator
        if line.startswith('|-'):
            if current_row is not None:
                rows.append(current_row)
            current_row = []
            continue

        # Header or data cells
        if line.startswith('!') or line.startswith('|'):
            if current_row is None:
                current_row = []

            is_header = line.startswith('!')
            line_content = line[1:].strip()

            # Special case: if line_content is empty, treat as one empty cell
            if not line_content:
                cells_text = ['']
            else:
                # Check for inline cells (!! or ||)
                delimiter = '!!' if is_header else '||'
                cells_text = _split_inline_cells(line_content, delimiter)

            for cell_text in cells_text:
                cell_text = cell_text.strip()

                # Parse attributes
                attrs, colspan, rowspan = _parse_cell_attributes(cell_text)

                # Extract content (after | if present, else the whole thing minus leading attrs)
                content = cell_text
                found_pipe = False
                if '|' in cell_text:
                    # Find the split position again (already done in _parse_cell_attributes)
                    depth_curly = 0
                    depth_bracket = 0
                    for i, char in enumerate(cell_text):
                        if char == '{' and i + 1 < len(cell_text) and cell_text[i + 1] == '{':
                            depth_curly += 1
                        elif char == '}' and i + 1 < len(cell_text) and cell_text[i + 1] == '}':
                            depth_curly -= 1
                        elif char == '[' and i + 1 < len(cell_text) and cell_text[i + 1] == '[':
                            depth_bracket += 1
                        elif char == ']' and i + 1 < len(cell_text) and cell_text[i + 1] == ']':
                            depth_bracket -= 1
                        elif char == '|' and depth_curly == 0 and depth_bracket == 0:
                            content = cell_text[i+1:].strip()
                            found_pipe = True
                            break

                if not found_pipe:
                    # Glued form or no attributes - remove leading attribute if present
                    attr_match = re.match(r'^\w+(?:-\w+)*=(["\'])([^"\']*?)\1\s+', cell_text)
                    if attr_match:
                        content = cell_text[attr_match.end():].strip()

                cell = Cell(
                    content=content,
                    is_header=is_header,
                    rowspan=rowspan,
                    colspan=colspan,
                    attributes=attrs if attrs else None
                )
                current_row.append(cell)
        else:
            # Multi-line cell content
            if current_row and current_row:
                current_row[-1].content += '\n' + line

    # Don't forget the last row
    if current_row is not None:
        rows.append(current_row)

    # Expand rowspan/colspan into a regular grid
    result = []
    for row in rows:
        # Check if this is a group header (single cell with large colspan >= 3)
        # Small colspans (2) are treated as normal headers
        if len(row) == 1 and row[0].colspan >= 3:
            # Unmask the content before adding
            content = _unmask_content(row[0].content, replacements)
            result.append({"_group_label": content})
            continue

        # Build row dict
        row_dict = {}
        col_idx = 0

        for cell in row:
            # Skip columns occupied by rowspan from previous rows
            while col_idx in rowspan_carry:
                row_dict[str(col_idx)] = rowspan_carry[col_idx].content
                if rowspan_carry[col_idx].rowspan <= 1:
                    del rowspan_carry[col_idx]
                else:
                    rowspan_carry[col_idx] = Cell(
                        content=rowspan_carry[col_idx].content,
                        is_header=rowspan_carry[col_idx].is_header,
                        rowspan=rowspan_carry[col_idx].rowspan - 1,
                        colspan=1,
                        attributes=rowspan_carry[col_idx].attributes
                    )
                col_idx += 1

            # Place this cell and handle colspan
            # Unmask content before placing
            unmasked_content = _unmask_content(cell.content, replacements)
            for span_offset in range(cell.colspan):
                row_dict[str(col_idx + span_offset)] = unmasked_content

            # Track rowspan for future rows
            if cell.rowspan > 1:
                for span_offset in range(cell.colspan):
                    rowspan_carry[col_idx + span_offset] = Cell(
                        content=unmasked_content,
                        is_header=cell.is_header,
                        rowspan=cell.rowspan - 1,
                        colspan=1,
                        attributes=cell.attributes
                    )

            col_idx += cell.colspan

        # Fill remaining rowspan cells
        while col_idx in rowspan_carry:
            row_dict[str(col_idx)] = rowspan_carry[col_idx].content
            if rowspan_carry[col_idx].rowspan <= 1:
                del rowspan_carry[col_idx]
            else:
                rowspan_carry[col_idx] = Cell(
                    content=rowspan_carry[col_idx].content,
                    is_header=rowspan_carry[col_idx].is_header,
                    rowspan=rowspan_carry[col_idx].rowspan - 1,
                    colspan=1,
                    attributes=rowspan_carry[col_idx].attributes
                )
            col_idx += 1

        if row_dict:
            result.append(row_dict)

    return result
