#!/usr/bin/env python
"""topo-sort: order tasks by their dependencies (Kahn's algorithm).

Input format (one rule per line, '#' starts a comment):

    app: lib utils      # app depends on lib and utils
    lib: utils
    docs                # a node with no dependencies

Dependencies are emitted before the things that depend on them.
"""
import argparse
import heapq
import json
import sys


class CycleError(Exception):
    def __init__(self, cycle):
        self.cycle = cycle
        super().__init__("cycle detected: " + " -> ".join(cycle))


def parse(text):
    """Parse dependency text into {node: set(deps)}. Every mentioned node is a key."""
    graph = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" in line:
            head, _, tail = line.partition(":")
            node = head.strip()
            deps = tail.replace(",", " ").split()
        else:
            parts = line.split()
            if len(parts) != 1:
                raise ValueError(f"line {lineno}: expected 'node: deps...' or a single node, got {raw!r}")
            node, deps = parts[0], []
        if not node or any(c.isspace() for c in node):
            raise ValueError(f"line {lineno}: bad node name {node!r}")
        graph.setdefault(node, set()).update(deps)
        for d in deps:
            graph.setdefault(d, set())
    return graph


def find_cycle(graph):
    """Return one cycle as a list [a, b, ..., a], or None. Iterative DFS, deterministic."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    for start in sorted(graph):
        if color[start] != WHITE:
            continue
        stack = [(start, iter(sorted(graph[start])))]
        path = [start]
        color[start] = GREY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
                path.pop()
            elif color[nxt] == GREY:
                return path[path.index(nxt):] + [nxt]
            elif color[nxt] == WHITE:
                color[nxt] = GREY
                stack.append((nxt, iter(sorted(graph[nxt]))))
                path.append(nxt)
    return None


def levels(graph):
    """Group nodes into levels: level 0 has no deps; level k depends only on levels < k.
    Nodes inside a level can run in parallel. Raises CycleError."""
    indeg = {n: len(d) for n, d in graph.items()}
    dependents = {n: [] for n in graph}
    for n, deps in graph.items():
        for d in deps:
            dependents[d].append(n)
    current = sorted(n for n, k in indeg.items() if k == 0)
    out, seen = [], 0
    while current:
        out.append(current)
        seen += len(current)
        nxt = []
        for n in current:
            for m in dependents[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    nxt.append(m)
        current = sorted(nxt)
    if seen != len(graph):
        raise CycleError(find_cycle(graph))
    return out


def order(graph):
    """Lexicographically smallest valid topological order (Kahn + min-heap). Raises CycleError."""
    indeg = {n: len(d) for n, d in graph.items()}
    dependents = {n: [] for n in graph}
    for n, deps in graph.items():
        for d in deps:
            dependents[d].append(n)
    heap = [n for n, k in indeg.items() if k == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        n = heapq.heappop(heap)
        out.append(n)
        for m in dependents[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, m)
    if len(out) != len(graph):
        raise CycleError(find_cycle(graph))
    return out


def closure(graph, targets):
    """All transitive dependencies of targets (including targets), as a subgraph."""
    missing = [t for t in targets if t not in graph]
    if missing:
        raise KeyError("unknown node(s): " + ", ".join(missing))
    keep, stack = set(), list(targets)
    while stack:
        n = stack.pop()
        if n not in keep:
            keep.add(n)
            stack.extend(graph[n])
    return {n: set(graph[n]) for n in keep}


def main(argv=None):
    p = argparse.ArgumentParser(description="Topologically sort a dependency file (deps first).")
    p.add_argument("file", nargs="?", default="-", help="dependency file, '-' for stdin (default)")
    p.add_argument("-l", "--levels", action="store_true", help="print parallel levels instead of a flat order")
    p.add_argument("-t", "--target", action="append", default=[], help="only what TARGET needs (repeatable)")
    p.add_argument("--reverse", action="store_true", help="dependents first (teardown order)")
    p.add_argument("--json", action="store_true", help="JSON output")
    a = p.parse_args(argv)

    try:
        text = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
        graph = parse(text)
        if a.target:
            graph = closure(graph, a.target)
        result = levels(graph) if a.levels else order(graph)
    except CycleError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, OSError) as e:
        msg = e.args[0] if isinstance(e, KeyError) else e
        print(f"error: {msg}", file=sys.stderr)
        return 2

    if a.reverse:
        result = result[::-1]
    if a.json:
        print(json.dumps(result))
    elif a.levels:
        for i, lvl in enumerate(result):
            print(f"{i}: {' '.join(lvl)}")
    else:
        print("\n".join(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
