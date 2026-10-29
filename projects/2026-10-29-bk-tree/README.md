# bk-tree

Fuzzy "did you mean?" word lookup backed by a **BK-tree** (Burkhard-Keller tree)
under Levenshtein edit distance. Pure Python standard library.

## How it works

Every node stores one word. Its children are keyed by their exact edit distance
to that word. To find all words within distance `d` of query `q`:

1. Compute `dist = D(q, node)`. If `dist <= d`, report the node.
2. Visit only children whose key `k` is in `[dist - d, dist + d]`.

Why that's safe: edit distance is a metric, so by the triangle inequality any
word `w` below child `k` satisfies `D(q, w) >= |dist - k|`. If `|dist - k| > d`,
nothing in that subtree can match, and it is skipped entirely.

For small radii this skips most of the dictionary: in the test suite, a radius-1
search over ~4,900 random words computes only ~530 distances (about 11%).

`levenshtein()` is a two-row DP with an optional `limit` for early exit.

## Usage

```
python bktree.py WORDLIST QUERY... [-d MAX_DIST] [-n LIMIT] [-i] [--stats] [--json]
```

- `-d` max edit distance (default 2)
- `-n` max suggestions per query (default 5, `0` = all)
- `-i` case-insensitive
- `--stats` show distance computations vs. a linear scan
- Exit code: `0` all queries matched, `1` some query had no match, `2` file error

A sample 55-word programming vocabulary is in `words.txt`.

```
$ python bktree.py words.txt fucntion recusion strng queue xyzzyq --stats
fucntion: ? -> function (2)  [41/55 compared, 75%]
recusion: ? -> recursion (1)  [46/55 compared, 84%]
strng: ? -> string (1)  [47/55 compared, 85%]
queue: ok  [47/55 compared, 85%]
xyzzyq: no match  [49/55 compared, 89%]
$ echo $?
1
```

(On a tiny list pruning saves little; it pays off on large dictionaries.)

```
$ python bktree.py words.txt -d 3 -n 3 complier --json
{
  "words": 55,
  "depth": 6,
  "max_dist": 3,
  "results": [
    {
      "query": "complier",
      "exact": false,
      "visited": 49,
      "matches": [
        {
          "word": "compiler",
          "distance": 2
        },
        {
          "word": "compile",
          "distance": 3
        }
      ]
    }
  ]
}
```

### As a library

```python
from bktree import BKTree
tree = BKTree(["book", "books", "cake", "boo", "cook"])
tree.search("bok", 1)      # [(1, 'boo'), (1, 'book')]
tree.closest("cakes", 1)   # [(1, 'cake')]
"cake" in tree             # True
```

## Tests

```
python -m unittest -v
```

15 tests: known distances, early-exit limit, duplicates, empty tree, a
randomized brute-force comparison (60 queries x 4 radii over 400 words),
a pruning-effectiveness check, and CLI text/JSON/exit-code behavior.
