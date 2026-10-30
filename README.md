# daily-builds

A new small project every day: Python/JS utilities, CLI tools, and algorithms.
Each project lives in `projects/YYYY-MM-DD-name/` with its own README and tests.

## Projects

| Date | Project | Language | Description |
|------|---------|----------|-------------|
| 2026-10-06 | [cron-next](projects/2026-10-06-cron-next/) | Python | Parse 5-field cron expressions and list the next run times |
| 2026-10-07 | [json-diff](projects/2026-10-07-json-diff/) | JavaScript | Structural diff of two JSON files as JSON paths, with ignore and numeric tolerance |
| 2026-10-08 | [bloom-filter](projects/2026-10-08-bloom-filter/) | Python | Bloom filter with optimal sizing, double hashing, union, JSON persistence, and a CLI |
| 2026-10-10 | [sudoku-solver](projects/2026-10-10-sudoku-solver/) | JavaScript | Sudoku solver with bitmask constraint propagation, MRV backtracking, and uniqueness check |
| 2026-10-13 | [semver-tool](projects/2026-10-13-semver-tool/) | Python | SemVer 2.0.0 parse/compare/sort/bump plus npm-style range matching (^, ~, x, hyphen, \|\|) |
| 2026-10-15 | [md-toc](projects/2026-10-15-md-toc/) | JavaScript | Markdown TOC generator with GitHub-compatible slugs, in-place marker injection, and a CI --check mode |
| 2026-10-16 | [myers-diff](projects/2026-10-16-myers-diff/) | Python | Myers O(ND) line diff from scratch with unified hunks, -U context, --stat, and color |
| 2026-10-17 | [env-check](projects/2026-10-17-env-check/) | JavaScript | Lint .env files and diff them against .env.example: missing/extra/duplicate/empty keys, quoting, CI exit codes |
| 2026-10-18 | [exact-calc](projects/2026-10-18-exact-calc/) | Python | Exact rational calculator: shunting-yard to RPN, Fraction math, functions, variables, exact sqrt |
| 2026-10-19 | [dupe-find](projects/2026-10-19-dupe-find/) | JavaScript | Find duplicate files via size, 4 KiB prefix hash, then full SHA-256; reclaimable-space report, JSON, CI exit codes |
| 2026-10-20 | [huffman](projects/2026-10-20-huffman/) | Python | Canonical Huffman coder: compress/decompress files, code table vs. Shannon entropy, corruption checks |
| 2026-10-21 | [cidr-calc](projects/2026-10-21-cidr-calc/) | JavaScript | IPv4 subnet calculator: info, contains (exit codes), split, and minimal CIDR summarize of ranges |
| 2026-10-22 | [topo-sort](projects/2026-10-22-topo-sort/) | Python | Dependency sorter: Kahn topological order, parallel levels, target closure, cycle path reporting |
| 2026-10-23 | [countdown-solver](projects/2026-10-23-countdown-solver/) | JavaScript | Countdown numbers-game solver: fewest-ops exact answer or closest, deduplicated --all solutions, JSON, exit codes |
| 2026-10-25 | [csv-peek](projects/2026-10-25-csv-peek/) | Python | CSV previewer and profiler: sniffed delimiter, aligned table, per-column type inference, nulls/distinct/min/max/mean/top, JSON |
| 2026-10-26 | [template-engine](projects/2026-10-26-template-engine/) | JavaScript | Zero-dependency template engine supporting variables, dot notation, custom filters, conditionals, and loops |
| 2026-10-29 | [bk-tree](projects/2026-10-29-bk-tree/) | Python | BK-tree fuzzy word lookup: Levenshtein with early exit, triangle-inequality pruning, did-you-mean CLI, JSON, exit codes |
| 2026-10-30 | [jwt-inspect](projects/2026-10-30-jwt-inspect/) | JavaScript | Offline JWT debugger: decode header/payload, exp/nbf/iat status with leeway, HS256/384/512 verify and sign, JSON, exit codes |
