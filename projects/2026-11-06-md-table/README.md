# md-table

Zero-dependency Python utility and CLI for parsing, aligning, sorting, and formatting Markdown tables.

## Features

- **Parse & Format**: Normalizes spacing, column padding, and cell alignments (`left`, `right`, `center`).
- **Sorting**: Sort rows alphabetically or numerically by column name or index.
- **Validation**: `--check` mode for CI/CD pipelines to ensure tables are correctly formatted.
- **Standard Library Only**: No external dependencies.

## Usage

```bash
python projects/2026-11-06-md-table/md_table.py table.md
```

### Options

- `--sort <column>`: Sort rows by column name or 0-based index.
- `--reverse`: Reverse sort order.
- `--numeric`: Parse numbers for numeric sorting.
- `--align <alignments>`: Set comma-separated alignments (`left`, `right`, `center`).
- `--check`: Exit with non-zero status if table is not formatted.

### Example

Input:
```markdown
| Product | Price | Qty |
|---|---|---|
| Apple | $1.20 | 10 |
| Banana | $0.80 | 25 |
| Orange | $1.50 | 15 |
```

Command:
```bash
python projects/2026-11-06-md-table/md_table.py --sort Price --numeric input.md
```

Output:
```markdown
| Product | Price | Qty |
| ------- | ----- | --- |
| Banana  | $0.80 | 25  |
| Apple   | $1.20 | 10  |
| Orange  | $1.50 | 15  |
```

## Tests

Run tests with unittest:
```bash
python -m unittest projects/2026-11-06-md-table/test_md_table.py
```
