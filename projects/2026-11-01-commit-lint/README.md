# commit-lint

Zero-dependency [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) linter for Node. It checks one message (argument, file or stdin) or every commit in a git range. Use it in a `commit-msg` hook or in CI.

## What it checks

Errors (exit 1):

- `header-format`: header must match `type(scope)!: subject`
- `type-enum` / `type-case`: type must be in the allowed list and lower-case
- `scope-empty`, `scope-enum`, `scope-required`
- `header-separator`: exactly `": "` after the type/scope
- `subject-empty`, `subject-full-stop`
- `header-max-length` (default 72)
- `body-leading-blank`: blank line between header and body
- `footer-breaking-case`: `BREAKING CHANGE` must be upper-case

Warnings (errors with `--strict`):

- `subject-case`: subject should start lower-case
- `subject-mood`: "added"/"fixes" style instead of imperative
- `breaking-description`: `!` with no body and no `BREAKING CHANGE` footer
- `body-max-line-length` (100, URLs exempt)

Git comment lines (`# ...`) are stripped. Merge and auto-revert commits are skipped in `--git` mode. A `BREAKING CHANGE:` footer or `!` marks the commit `[BREAKING]`.

## Usage

```
node commit-lint.js [options] [message]
  -f, --file PATH    read message from file (e.g. .git/COMMIT_EDITMSG)
  -g, --git RANGE    lint every commit in git range (e.g. origin/main..HEAD)
  --types a,b,c      allowed types
  --scopes a,b       allowed scopes (default: any)
  --require-scope    scope is mandatory
  --max N            header max length (default 72)
  --strict           treat warnings as errors
  --json             JSON output
exit: 0 ok, 1 lint errors, 2 usage/IO error
```

In a message argument, a literal `\n` becomes a newline.

## Examples (real output)

```
$ node commit-lint.js "feat(api): add rate limiter"
ok   arg  feat(api): add rate limiter
1 checked, 0 failed
exit 0

$ printf 'Fixed The Bug.\nmore text\n' | node commit-lint.js
FAIL stdin  Fixed The Bug.
     error  header-format: header must match "type(scope)!: subject"
     error  body-leading-blank: blank line required between header and body
1 checked, 1 failed
exit 1

$ node commit-lint.js --strict 'feat(api)!: Removed v1 routes'
FAIL arg  feat(api)!: Removed v1 routes  [BREAKING]
     error  subject-case: subject should start lower-case
     error  subject-mood: use imperative mood ("add", not "added"/"adds")
     error  breaking-description: "!" used without a BREAKING CHANGE footer or body explaining it
1 checked, 1 failed
exit 1
```

Run against this repo's own history:

```
$ node commit-lint.js --git HEAD~4..HEAD
FAIL 81d7e4d  feat(nonogram-solver): DP line-solving nonogram solver with search and uniqueness check
     error  header-max-length: header is 87 chars (max 72)
FAIL b9294c6  feat(jwt-inspect): offline JWT decoder with claim checks and HMAC verify/sign
     error  header-max-length: header is 77 chars (max 72)
ok   581a76d  feat(bk-tree): BK-tree fuzzy word lookup with did-you-mean CLI
ok   0d5c8a0  feat(template-engine): zero-dependency JS template engine
4 checked, 2 failed
exit 1
```

```
$ node commit-lint.js --json 'fix(db): retry on deadlock\n\nBREAKING CHANGE: retries now default to 3'
{
  "checked": 1,
  "failed": 0,
  "results": [
    {
      "id": "arg",
      "header": "fix(db): retry on deadlock",
      "valid": true,
      "breaking": true,
      "errors": [],
      "warnings": []
    }
  ]
}
```

### As a git hook

```sh
# .git/hooks/commit-msg
#!/bin/sh
exec node /path/to/commit-lint.js --file "$1"
```

### In CI

```sh
node commit-lint.js --git origin/main..HEAD
```

## Library

```js
const { lint, parse } = require('./commit-lint.js');
lint('feat: add x', { scopes: ['api'], headerMax: 50 }); // { valid, errors, warnings, parsed }
```

## Tests

```
node --test
```

14 tests: parsing, every rule, CLI exit codes, `--file`, and `--git` against a temporary repository (needs `git` on PATH).
