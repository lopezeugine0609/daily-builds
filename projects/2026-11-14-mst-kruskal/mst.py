#!/usr/bin/env python
"""Minimum spanning tree from an edge list: Kruskal (union-find) and Prim (heap).

Input lines: "u v weight" (whitespace or comma separated). '#' starts a comment.
Weights are parsed as exact Fractions, so "1/3" and "0.1" sum without float error.
"""
import argparse
import heapq
import json
import sys
from collections import defaultdict
from fractions import Fraction

EXIT_OK, EXIT_INPUT, EXIT_DISCONNECTED, EXIT_MISMATCH = 0, 1, 3, 4


class GraphError(ValueError):
    pass


class UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.size = {x: 1 for x in items}

    def find(self, x):
        p = self.parent
        while p[x] != x:
            p[x] = p[p[x]]  # path halving
            x = p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True


def parse_edges(text):
    """Return list of (u, v, Fraction weight). Self-loops are kept but never used in the tree."""
    edges = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].replace(",", " ").strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise GraphError(f"line {lineno}: expected 'u v weight', got {raw.strip()!r}")
        u, v, w_text = parts
        try:
            w = Fraction(w_text)
        except (ValueError, ZeroDivisionError):
            raise GraphError(f"line {lineno}: weight {w_text!r} is not a finite number")
        edges.append((u, v, w))
    return edges


def _key(edge):
    u, v, w = edge
    return (w, min(u, v), max(u, v))


def kruskal(nodes, edges):
    uf = UnionFind(nodes)
    tree = []
    for u, v, w in sorted(edges, key=_key):
        if uf.union(u, v):
            tree.append((u, v, w))
    return tree


def prim(nodes, edges):
    adj = defaultdict(list)
    for u, v, w in edges:
        if u != v:
            adj[u].append((w, v))
            adj[v].append((w, u))
    tree, seen = [], set()
    for start in nodes:
        if start in seen:
            continue
        seen.add(start)
        heap = [(w, start, v) for w, v in adj[start]]
        heapq.heapify(heap)
        while heap:
            w, u, v = heapq.heappop(heap)
            if v in seen:
                continue
            seen.add(v)
            tree.append((u, v, w))
            for w2, x in adj[v]:
                if x not in seen:
                    heapq.heappush(heap, (w2, v, x))
    return tree


def solve(edges, algo):
    nodes = sorted({u for u, _, _ in edges} | {v for _, v, _ in edges})
    tree = kruskal(nodes, edges) if algo == "kruskal" else prim(nodes, edges)
    tree = [(min(u, v), max(u, v), w) for u, v, w in tree]  # canonical endpoint order
    tree.sort(key=_key)
    total = sum((w for _, _, w in tree), Fraction(0))
    return {
        "algo": algo,
        "nodes": len(nodes),
        "tree": tree,
        "components": len(nodes) - len(tree),
        "total": total,
    }


def fmt_number(x):
    return x.numerator if x.denominator == 1 else float(x)


def render_text(res, verified):
    lines = [
        f"{res['algo']}: {res['nodes']} nodes, {len(res['tree'])} edges, "
        f"{res['components']} component(s)",
    ]
    total = res["total"]
    if total.denominator == 1:
        lines.append(f"total weight: {total.numerator}")
    else:
        lines.append(f"total weight: {float(total):g} (exact {total})")
    for u, v, w in res["tree"]:
        lines.append(f"  {u} {v} {fmt_number(w)}")
    if verified is not None:
        lines.append("verify: kruskal and prim agree")
    return "\n".join(lines)


def render_json(res, verified):
    return json.dumps(
        {
            "algorithm": res["algo"],
            "nodes": res["nodes"],
            "components": res["components"],
            "total_weight": fmt_number(res["total"]),
            "total_exact": str(res["total"]),
            "verified": verified,
            "tree": [
                {"u": u, "v": v, "weight": fmt_number(w)} for u, v, w in res["tree"]
            ],
        },
        indent=2,
    )


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="mst",
        description="Minimum spanning tree (Kruskal or Prim) of an undirected weighted edge list.",
        epilog="exit: 0 ok, 1 input error, 3 disconnected (without --forest), 4 --verify mismatch",
    )
    p.add_argument("file", nargs="?", default="-", help="edge list file, or - for stdin")
    p.add_argument("--algo", choices=["kruskal", "prim"], default="kruskal")
    p.add_argument("--verify", action="store_true", help="run the other algorithm too; totals must match")
    p.add_argument("--forest", action="store_true", help="allow disconnected input; output a spanning forest")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args(argv)

    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        edges = parse_edges(text)
    except (OSError, GraphError) as e:
        print(f"mst: {e}", file=sys.stderr)
        return EXIT_INPUT
    if not edges:
        print("mst: no edges in input", file=sys.stderr)
        return EXIT_INPUT

    res = solve(edges, args.algo)
    verified = None
    if args.verify:
        other = solve(edges, "prim" if args.algo == "kruskal" else "kruskal")
        verified = other["total"] == res["total"] and len(other["tree"]) == len(res["tree"])
        if not verified:
            print(
                f"mst: MISMATCH {args.algo}={res['total']} vs {other['algo']}={other['total']}",
                file=sys.stderr,
            )
            return EXIT_MISMATCH
    if res["components"] > 1 and not args.forest:
        print(
            f"mst: graph has {res['components']} components; use --forest for a spanning forest",
            file=sys.stderr,
        )
        return EXIT_DISCONNECTED

    print(render_json(res, verified) if args.json else render_text(res, verified))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
