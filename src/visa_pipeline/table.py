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
    lines = table_text.strip().split('\n')
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

            # Check for inline cells (!! or ||)
            delimiter = '!!' if is_header else '||'
            cells_text = _split_inline_cells(line_content, delimiter)

            for cell_text in cells_text:
                cell_text = cell_text.strip()
                if not cell_text:
                    continue

                # Parse attributes
                attrs, colspan, rowspan = _parse_cell_attributes(cell_text)

                # Extract content (after | if present, else the whole thing minus leading attrs)
                content = cell_text
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
                            break
                else:
                    # Glued form or no attributes - remove leading attribute if present
                    attr_match = re.match(r'^\w+(?:-\w+)*=["\']?[^"\']*["\']?\s+', cell_text)
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
        # Check if this is a group header (single cell with large colspan)
        if len(row) == 1 and row[0].colspan > 1:
            result.append({"_group_label": row[0].content})
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
            for span_offset in range(cell.colspan):
                row_dict[str(col_idx + span_offset)] = cell.content

            # Track rowspan for future rows
            if cell.rowspan > 1:
                for span_offset in range(cell.colspan):
                    rowspan_carry[col_idx + span_offset] = Cell(
                        content=cell.content,
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
