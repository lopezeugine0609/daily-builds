# slug-rename

Batch-rename the files in one directory to lowercase ASCII slugs, in plain Node.js (no dependencies). Dry run by default. Name collisions get a numeric suffix, never an overwrite. Every `--apply` writes a journal so `--undo` can revert it.

## How it works

- Stem: accents stripped (NFKD), lowercased, every run of non `[a-z0-9]` becomes `-`, leading and trailing `-` removed. Empty stem becomes `file`.
- Extension: kept, lowercased, non-alphanumerics removed (`.PDF` becomes `.pdf`).
- Dotfiles are never touched. Subdirectories are never touched (files only, not recursive).
- Collisions are checked case-insensitively, the way Windows and macOS see names. A clash with an existing file or an earlier target gets `-2`, `-3`, and so on. Case-only changes such as `README.md` to `readme.md` are allowed.
- `--apply` renames in order and writes `.slug-rename-journal.json`. It refuses to run while a journal exists.
- `--undo` reverses the journal, newest first. A rename is blocked (and kept in the journal) if the original name is now taken or the file is missing.

## Usage

```
usage: slug-rename.js [--apply] [--json] [DIR]
       slug-rename.js --undo [DIR]
  DIR       directory to process (default: .), files only, not recursive
  --apply   rename for real (default is a dry run that only prints the plan)
  --undo    revert the last --apply using .slug-rename-journal.json
  --json    machine-readable output
  exit 0 = ok, 2 = usage or IO error
```

Example directory:

```
$ ls
!!!.txt  Café Menu.md  Meeting notes.txt  meeting-notes.txt  My Résumé (final).PDF  README.md
```

Dry run (changes nothing):

```
$ node slug-rename.js .
!!!.txt -> file.txt
Café Menu.md -> cafe-menu.md
Meeting notes.txt -> meeting-notes-2.txt  (collision: suffixed)
My Résumé (final).PDF -> my-resume-final.pdf
README.md -> readme.md
dry run: 5 to rename, 1 unchanged (add --apply to rename)
exit=0
```

Apply, then undo:

```
$ node slug-rename.js --apply .
...
renamed 5 file(s); undo with --undo. journal: .slug-rename-journal.json
$ ls -a
.  ..  .slug-rename-journal.json  cafe-menu.md  file.txt  meeting-notes.txt  meeting-notes-2.txt  my-resume-final.pdf  readme.md

$ node slug-rename.js --undo .
restored readme.md -> README.md
restored my-resume-final.pdf -> My Résumé (final).PDF
restored meeting-notes-2.txt -> Meeting notes.txt
restored cafe-menu.md -> Café Menu.md
restored file.txt -> !!!.txt
5 restored, 0 blocked
exit=0
```

Note that `meeting-notes.txt` was already clean, so it was left alone and `Meeting notes.txt` got the `-2` suffix.

## Tests

Node built-in test runner, no install needed:

```
node --test
```

Current result:

```
ℹ tests 13
ℹ pass 13
ℹ fail 0
```

The tests cover slug rules, dotfile skipping, collision suffixes (including between two renamed files), case-only renames, the journal round trip, refusal to overwrite an existing journal, undo blocking when the original name is reused, and CLI exit codes.
