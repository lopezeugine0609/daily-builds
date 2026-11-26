#!/usr/bin/env python
"""grid-path: shortest paths on ASCII grid maps (BFS, Dijkstra, A*).

Map legend:
  S start, G goal, # wall, . open (cost 1), digits 1-9 = terrain cost,
  ~ water (cost 5). Anything else is treated as open (cost 1).

Moving INTO a cell costs that cell's cost. Diagonal moves (--diag) cost
cost * sqrt(2) and may not cut corners between two walls.
"""
import argparse
import heapq
import json
import math
import sys
from collections import deque

WALL = "#"
SQRT2 = math.sqrt(2)


class GridError(ValueError):
    pass


class Grid:
    def __init__(self, text):
        lines = [ln.rstrip("\r\n") for ln in text.splitlines()]
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            raise GridError("empty map")
        self.w = max(len(ln) for ln in lines)
        self.h = len(lines)
        self.cells = [ln.ljust(self.w, WALL) for ln in lines]
        self.start = self._find("S")
        self.goal = self._find("G")

    def _find(self, ch):
        hits = [(r, c) for r, row in enumerate(self.cells)
                for c, v in enumerate(row) if v == ch]
        if len(hits) != 1:
            raise GridError(f"map needs exactly one '{ch}', found {len(hits)}")
        return hits[0]

    def cost(self, pos):
        ch = self.cells[pos[0]][pos[1]]
        if ch.isdigit() and ch != "0":
            return int(ch)
        if ch == "~":
            return 5
        return 1

    def passable(self, pos):
        r, c = pos
        return 0 <= r < self.h and 0 <= c < self.w and self.cells[r][c] != WALL

    def neighbors(self, pos, diag=False):
        r, c = pos
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (r + dr, c + dc)
            if self.passable(n):
                yield n, float(self.cost(n))
        if diag:
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                n = (r + dr, c + dc)
                if not self.passable(n):
                    continue
                # no corner cutting: both orthogonal side cells must be open
                if not (self.passable((r + dr, c)) and self.passable((r, c + dc))):
                    continue
                yield n, self.cost(n) * SQRT2


def _rebuild(came, node):
    path = [node]
    while node in came:
        node = came[node]
        path.append(node)
    return path[::-1]


def path_cost(grid, path):
    total = 0.0
    for a, b in zip(path, path[1:]):
        step = grid.cost(b)
        total += step * SQRT2 if a[0] != b[0] and a[1] != b[1] else step
    return total


def bfs(grid, diag=False):
    """Fewest steps, ignores terrain cost."""
    start, goal = grid.start, grid.goal
    came, seen, q, expanded = {}, {start}, deque([start]), 0
    while q:
        cur = q.popleft()
        expanded += 1
        if cur == goal:
            return _rebuild(came, cur), expanded
        for n, _ in grid.neighbors(cur, diag):
            if n not in seen:
                seen.add(n)
                came[n] = cur
                q.append(n)
    return None, expanded


def heuristic(a, b, diag):
    dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
    if diag:  # octile distance, admissible since min cost is 1
        return (dr + dc) + (SQRT2 - 2) * min(dr, dc)
    return dr + dc  # manhattan


def astar(grid, diag=False, use_heuristic=True):
    """A* (or Dijkstra when use_heuristic=False). Optimal by cost."""
    start, goal = grid.start, grid.goal
    h = (lambda p: heuristic(p, goal, diag)) if use_heuristic else (lambda p: 0.0)
    g = {start: 0.0}
    came, closed, expanded, tie = {}, set(), 0, 0
    heap = [(h(start), h(start), 0, start)]
    while heap:
        _, _, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        expanded += 1
        if cur == goal:
            return _rebuild(came, cur), expanded
        for n, step in grid.neighbors(cur, diag):
            ng = g[cur] + step
            if ng < g.get(n, math.inf) - 1e-12:
                g[n] = ng
                came[n] = cur
                tie += 1
                hn = h(n)
                # ties on f broken by smaller h (deeper node) to expand less
                heapq.heappush(heap, (ng + hn, hn, tie, n))
    return None, expanded


def dijkstra(grid, diag=False):
    return astar(grid, diag, use_heuristic=False)


ALGOS = {"bfs": bfs, "dijkstra": dijkstra, "astar": astar}


def render(grid, path, mark="*"):
    rows = [list(r) for r in grid.cells]
    for r, c in path or []:
        if rows[r][c] not in "SG":
            rows[r][c] = mark
    return "\n".join("".join(r).rstrip() for r in rows)


def solve(text, algo="astar", diag=False):
    grid = Grid(text)
    path, expanded = ALGOS[algo](grid, diag)
    return {
        "algorithm": algo,
        "diagonal": diag,
        "found": path is not None,
        "steps": len(path) - 1 if path else None,
        "cost": round(path_cost(grid, path), 4) if path else None,
        "expanded": expanded,
        "path": [list(p) for p in path] if path else [],
        "render": render(grid, path),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Shortest path on an ASCII grid map.")
    ap.add_argument("map", help="map file, or - for stdin")
    ap.add_argument("-a", "--algo", choices=[*ALGOS, "all"], default="astar")
    ap.add_argument("-d", "--diag", action="store_true", help="allow 8-way moves")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("-q", "--quiet", action="store_true", help="no map render")
    args = ap.parse_args(argv)

    try:
        if args.map == "-":
            text = sys.stdin.read()
        else:
            with open(args.map, encoding="utf-8") as f:
                text = f.read()
        algos = list(ALGOS) if args.algo == "all" else [args.algo]
        results = [solve(text, a, args.diag) for a in algos]
    except (OSError, GridError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        out = results if len(results) > 1 else results[0]
        print(json.dumps(out, indent=2))
    else:
        for i, r in enumerate(results):
            if i:
                print()
            if r["found"]:
                print(f"{r['algorithm']}: steps={r['steps']} cost={r['cost']:g} "
                      f"expanded={r['expanded']}")
            else:
                print(f"{r['algorithm']}: no path (expanded={r['expanded']})")
            if not args.quiet and r["found"]:
                print(r["render"])
    return 0 if all(r["found"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
