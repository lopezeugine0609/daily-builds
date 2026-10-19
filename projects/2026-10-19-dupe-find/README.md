# dupe-find

Find duplicate files by content. Node.js, standard library only. The script has no dependencies.

It uses three stages. Each stage only reads files that still collide after the stage before it:

1. **Group by size.** Only `lstat` is needed here, so a file with a unique size is never opened.
2. **SHA-256 of the first 4 KiB.** This applies to same-size files larger than 4 KiB. Big files that differ early are dropped after one small read.
3. **Full SHA-256.** It runs only on the remaining candidates. A group of two or more files with the same full hash is a duplicate group.

Other behavior:

- Symlinks are skipped.
- Hard links reached twice (same `dev:ino`) are counted once.
- Unreadable files are dropped silently.
- `.git` and `node_modules` are ignored by default.
- Groups are sorted by reclaimable bytes, largest first: `size × (copies − 1)`.

## Usage

```
node dupe-find.js [dir...] [--min-size N[k|m|g]] [--ignore NAME] [--no-default-ignore] [--json]
```

Exit codes: `0` means no duplicates, `1` means duplicates were found, `2` means an error. This lets you use it as a CI check.

Empty files are skipped by default (`--min-size` defaults to 1). Use `--min-size 0` to include them.

### Example (real output, Windows)

```
$ node dupe-find.js demo
6.6 KiB x 2  sha256:156ea8df3391
  demo\backup\2025\sunset-copy.jpg
  demo\photos\sunset.jpg
14 B x 3  sha256:9dacb5348028
  demo\backup\2025\notes-old.txt
  demo\backup\notes.txt
  demo\notes.txt
6 files scanned, 2 duplicate groups, 3 redundant files, 6.7 KiB reclaimable
$ echo $?
1
```

```
$ node dupe-find.js demo --min-size 1k --json
{
  "groups": [
    {
      "size": 6800,
      "hash": "156ea8df3391b549ce8bb30a8ecdbd7efe03b0d415b9c6581aa06006061a8dea",
      "paths": [
        "demo\\backup\\2025\\sunset-copy.jpg",
        "demo\\photos\\sunset.jpg"
      ]
    }
  ],
  "wasted": 6800,
  "stats": {
    "scanned": 2,
    "partialHashed": 2,
    "fullHashed": 2
  }
}
```

### As a library

```js
const { findDuplicates } = require('./dupe-find.js');
const { groups, wasted } = findDuplicates(['./photos'], { minSize: 1024 });
```

## Tests

```
node --test
```

10 tests cover these cases:

- grouping across subdirectories
- same-prefix files with different tails
- partial-hash pruning
- empty files
- default ignores
- sort order
- size parsing and formatting
- argument parsing
- CLI exit codes
