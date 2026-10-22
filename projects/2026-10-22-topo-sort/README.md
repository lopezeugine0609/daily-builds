# topo-sort

Order tasks by their dependencies, from the command line. Implements **Kahn's algorithm** for
topological sorting, with:

- a flat order (lexicographically smallest valid order, so output is deterministic),
- `--levels`: parallel "waves", where each level depends only on earlier levels,
- `--target`: only the transitive dependencies of the given node(s),
- `--reverse`: dependents first (teardown order),
- cycle detection that prints the **actual cycle path** (exit code 1).

Python 3, standard library only.

## Input format

One rule per line. `#` starts a comment. Dependencies may be separated by spaces or commas.

```
# build graph
app: lib, utils
lib: utils
tests: app
docs
```

`app: lib, utils` means *app depends on lib and utils*. A bare name (`docs`) is a node with no
dependencies. Nodes that appear only as dependencies are added automatically.

## Usage

```
python toposort.py [file] [-l] [-t TARGET ...] [--reverse] [--json]
```

`file` defaults to stdin (`-`).

```
$ python toposort.py example.deps
docs
utils
lib
app
tests

$ python toposort.py -l example.deps
0: docs utils
1: lib
2: app
3: tests

$ python toposort.py -t app --reverse --json example.deps
["app", "lib", "utils"]

$ printf "a: b\nb: c\nc: a\n" | python toposort.py; echo "exit $?"
error: cycle detected: a -> b -> c -> a
exit 1
```

Exit codes: `0` success, `1` cycle, `2` bad input or unknown target.

## How it works

1. **Kahn's algorithm.** Count each node's unmet dependencies (in-degree). Nodes with zero go into
   a ready set. Repeatedly remove a ready node, emit it, and decrement the count of everything that
   depends on it; nodes that reach zero become ready. O(V + E).
2. **Deterministic order.** The ready set is a min-heap, so the result is the lexicographically
   smallest topological order.
3. **Levels.** Instead of one node at a time, the whole ready set is emitted as one level. Every
   node in a level can run in parallel.
4. **Cycles.** If Kahn's algorithm emits fewer nodes than exist, the rest are on or behind a
   cycle. An iterative three-colour DFS (white/grey/black) then finds a back edge to a grey node
   and reports the path on the stack from that node.

## Tests

```
python -m unittest
```

17 tests: parsing, ordering (including a 60-node random DAG check), levels, cycles and self-loops,
target closure, and CLI exit codes.
