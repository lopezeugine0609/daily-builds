# mst: minimum spanning tree (Kruskal + Prim)

Reads an undirected weighted edge list and prints its minimum spanning tree or forest.
Kruskal uses union-find with path halving and union by size. Prim uses a binary heap.
Weights are exact `Fraction`s, so `1/3` and `0.1` add without float drift.
Standard library only.

## Input format

One edge per line: `u v weight`. Commas also work. `#` starts a comment. Self-loops are allowed and ignored.

```
# classic 7-node example, MST weight 39
A B 7
A D 5
B C 8
...
```

The full sample is in `sample.txt`.

## Usage

```
python mst.py sample.txt
python mst.py sample.txt --algo prim --verify
python mst.py sample.txt --json
python mst.py graph.txt --forest      # allow disconnected input
cat graph.txt | python mst.py -       # read from stdin
```

Real output:

```
$ python mst.py sample.txt
kruskal: 7 nodes, 6 edges, 1 component(s)
total weight: 39
  A D 5
  C E 5
  D F 6
  A B 7
  B E 7
  E G 9

$ python mst.py sample.txt --algo prim --verify
prim: 7 nodes, 6 edges, 1 component(s)
total weight: 39
  A D 5
  C E 5
  D F 6
  A B 7
  B E 7
  E G 9
verify: kruskal and prim agree

$ python mst.py sample.txt --json --verify
{
  "algorithm": "kruskal",
  "nodes": 7,
  "components": 1,
  "total_weight": 39,
  "total_exact": "39",
  "verified": true,
  ...
}
```

Disconnected input:

```
$ python mst.py dc.txt        # dc.txt: "A B 1" and "C D 2"
mst: graph has 2 components; use --forest for a spanning forest
$ echo $?
3

$ python mst.py dc.txt --forest
kruskal: 4 nodes, 2 edges, 2 component(s)
total weight: 3
  A B 1
  C D 2
```

## Options and exit codes

| Flag | Meaning |
|------|---------|
| `--algo kruskal\|prim` | Algorithm to use (default kruskal) |
| `--verify` | Also run the other algorithm; totals must match or exit 4 |
| `--forest` | Allow disconnected input and output a spanning forest |
| `--json` | JSON output with `total_weight`, `total_exact`, `verified`, and the tree |

| Exit | Meaning |
|------|---------|
| 0 | OK |
| 1 | Input error: unreadable file, bad line, bad weight, or no edges |
| 3 | Graph disconnected and `--forest` not given |
| 4 | `--verify` mismatch (should never happen; guards the implementations) |

## Tests

Standard library `unittest`, no dependencies:

```
python -m unittest -v
```

Covers parsing (comments, commas, bad input, exact fractions), the sample total of 39, self-loops, forests,
200 random connected graphs with negative weights where Kruskal and Prim totals agree and both return n-1 edges,
and CLI exit codes.

Result:

```
Ran 14 tests in 0.162s

OK
```
