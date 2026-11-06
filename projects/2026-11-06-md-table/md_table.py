#!/usr/bin/env python3
"""
Markdown Table Formatter & Aligner.
Parses, aligns, sorts, and formats Markdown tables.
"""

import sys
import argparse
import re
from typing import List, Tuple, Optional


class MarkdownTable:
    def __init__(self, headers: List[str], alignments: List[str], rows: List[List[str]]):
        self.headers = headers
        self.alignments = alignments  # 'left', 'right', 'center', or ''
        self.rows = rows

    @classmethod
    def parse(cls, content: str) -> "MarkdownTable":
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        table_lines = []
        for line in lines:
            if "|" in line:
                table_lines.append(line)
        
        if len(table_lines) < 2:
            raise ValueError("Invalid Markdown table: fewer than 2 lines with '|'")

        # Parse header
        headers = cls._parse_row(table_lines[0])
        
        # Parse delimiter (alignments)
        delim_cols = cls._parse_row(table_lines[1])
        alignments = []
        for col in delim_cols:
            col = col.strip()
            if col.startswith(":") and col.endswith(":"):
                alignments.append("center")
            elif col.endswith(":"):
                alignments.append("right")
            elif col.startswith(":"):
                alignments.append("left")
            else:
                alignments.append("")

        # Ensure alignments match header count
        while len(alignments) < len(headers):
            alignments.append("")

        # Parse rows
        rows = []
        for line in table_lines[2:]:
            cells = cls._parse_row(line)
            # Pad or truncate to match header count
            while len(cells) < len(headers):
                cells.append("")
            rows.append(cells[:len(headers)])

        return cls(headers, alignments, rows)

    @staticmethod
    def _parse_row(line: str) -> List[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        
        # Split by unescaped pipe
        cells = []
        current = []
        escaped = False
        for char in line:
            if escaped:
                current.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "|":
                cells.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        cells.append("".join(current).strip())
        return cells

    def sort_rows(self, col_idx: int, reverse: bool = False, numeric: bool = False) -> None:
        def sort_key(row):
            val = row[col_idx] if col_idx < len(row) else ""
            if numeric:
                # Try parsing as float/int, fallback to 0
                cleaned = re.sub(r"[^\d.-]", "", val)
                try:
                    if "." in cleaned:
                        return float(cleaned)
                    return int(cleaned)
                except ValueError:
                    return 0
            return val.lower()

        self.rows.sort(key=sort_key, reverse=reverse)

    def render(self) -> str:
        num_cols = len(self.headers)
        # Compute column widths
        widths = [len(h) for h in self.headers]
        for row in self.rows:
            for i, cell in enumerate(row):
                if i < num_cols:
                    widths[i] = max(widths[i], len(cell))
        
        # Ensure minimum width of 3 for delimiter
        for i in range(num_cols):
            widths[i] = max(widths[i], 3)

        # Format header
        header_cells = [h.ljust(widths[i]) for i, h in enumerate(self.headers)]
        header_line = "| " + " | ".join(header_cells) + " |"

        # Format delimiter
        delim_cells = []
        for i, align in enumerate(self.alignments):
            w = widths[i]
            if align == "left":
                delim_cells.append(":" + "-" * (w - 1))
            elif align == "right":
                delim_cells.append("-" * (w - 1) + ":")
            elif align == "center":
                delim_cells.append(":" + "-" * (w - 2) + ":")
            else:
                delim_cells.append("-" * w)
        delim_line = "| " + " | ".join(delim_cells) + " |"

        # Format rows
        rendered_rows = [header_line, delim_line]
        for row in self.rows:
            row_cells = []
            for i in range(num_cols):
                cell = row[i] if i < len(row) else ""
                align = self.alignments[i] if i < len(self.alignments) else ""
                w = widths[i]
                if align == "right":
                    row_cells.append(cell.rjust(w))
                elif align == "center":
                    row_cells.append(cell.center(w))
                else:
                    row_cells.append(cell.ljust(w))
            rendered_rows.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(rendered_rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Markdown Table Formatter & Aligner")
    parser.add_argument("file", nargs="?", help="Input markdown file (default: stdin)")
    parser.add_argument("--sort", help="Sort by column name or 0-based index")
    parser.add_argument("--reverse", action="store_true", help="Reverse sort order")
    parser.add_argument("--numeric", action="store_true", help="Numeric sort for --sort")
    parser.add_argument("--align", help="Set column alignments comma-separated (left,right,center)")
    parser.add_argument("--check", action="store_true", help="Check if table is already correctly formatted")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    try:
        table = MarkdownTable.parse(content)
    except Exception as e:
        print(f"Error parsing table: {e}", file=sys.stderr)
        sys.exit(1)

    if args.align:
        new_aligns = [a.strip().lower() for a in args.align.split(",")]
        for i, a in enumerate(new_aligns):
            if a in ("l", "left"):
                table.alignments[i] = "left"
            elif a in ("r", "right"):
                table.alignments[i] = "right"
            elif a in ("c", "center"):
                table.alignments[i] = "center"
            elif a in ("", "none"):
                table.alignments[i] = ""

    if args.sort is not None:
        col_idx = 0
        if args.sort.isdigit():
            col_idx = int(args.sort)
        else:
            found = False
            for i, h in enumerate(table.headers):
                if h.strip().lower() == args.sort.strip().lower():
                    col_idx = i
                    found = True
                    break
            if not found:
                print(f"Error: Column '{args.sort}' not found in headers {table.headers}", file=sys.stderr)
                sys.exit(1)
        table.sort_rows(col_idx, reverse=args.reverse, numeric=args.numeric)

    formatted = table.render()

    if args.check:
        if formatted.strip() != content.strip():
            print("Table is not formatted or aligned correctly.", file=sys.stderr)
            sys.exit(1)
        else:
            print("Table is correctly formatted.")
            sys.exit(0)

    sys.stdout.write(formatted)


if __name__ == "__main__":
    main()
