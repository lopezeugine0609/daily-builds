# md-toc

Generate a Markdown table of contents with **GitHub-compatible anchor links**, and keep it
up to date in place between marker comments. Zero dependencies (Node 18+).

- ATX (`## Title`, `## Title ##`) and setext (`===` / `---`) headings
- Ignores headings inside fenced code blocks (```` ``` ```` and `~~~`)
- GitHub slug rules: lowercase, punctuation stripped, spaces → `-`, Unicode letters kept,
  duplicates numbered `-1`, `-2`, … (numbering counts *all* headings, as GitHub does)
- Inline markup (links, code, bold/italic, HTML) stripped from labels and slugs
- `--write` injects between `<!-- toc -->` and `<!-- tocstop -->`; idempotent; preserves CRLF
- `--check` exits 1 if the TOC is stale — handy as a CI / pre-commit step

## Usage

```
usage: md-toc [options] <file.md ...>
  (no flag)     print the TOC to stdout
  -w, --write   inject TOC between <!-- toc --> and <!-- tocstop --> in place
  --check       exit 1 if a file's TOC is missing or stale (for CI)
  --min N       smallest heading level to include (default 1)
  --max N       largest heading level to include (default 6)
```

Print a TOC for the included [`sample.md`](sample.md):

```
$ node md-toc.js sample.md
- [My Project](#my-project)
  - [Install](#install)
  - [Usage](#usage)
    - [CLI flags](#cli-flags)
    - [config.json format](#configjson-format)
  - [FAQ](#faq)
    - [Why C++ & Rust?](#why-c--rust)
    - [Usage](#usage-1)
```

Check in CI, then fix in place (level 2 only):

```
$ node md-toc.js --check --min 2 sample.md; echo "exit=$?"
sample.md: TOC is out of date
exit=1

$ node md-toc.js -w --min 2 --max 2 s.md
s.md: updated

$ head -9 s.md
# My Project

<!-- toc -->

- [Install](#install)
- [Usage](#usage)
- [FAQ](#faq)

<!-- tocstop -->

$ node md-toc.js --check --min 2 --max 2 s.md; echo "exit=$?"
s.md: OK
exit=0
```

Exit codes: `0` ok, `1` stale/missing TOC under `--check`, `2` usage or I/O error.

Use as a library:

```js
const { buildToc, injectToc, slugify } = require('./md-toc.js');
slugify('What is `npm ci`?'); // 'what-is-npm-ci'
```

## Tests

```
node --test
```

11 tests (slugs, parsing, fences, setext, dedupe, min/max, injection, CRLF, CLI) — all passing.
