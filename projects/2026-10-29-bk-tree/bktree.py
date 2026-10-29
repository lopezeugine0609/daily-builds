#!/usr/bin/env python
"""BK-tree: fast "did you mean?" lookups under Levenshtein distance.

A BK-tree (Burkhard-Keller, 1973) indexes words in a metric space. Each node
holds one word; its children are keyed by their exact distance to that word.
To find every word within distance `d` of a query `q`:

    dist = D(q, node.word)
    if dist <= d: report node.word
    only visit children with key k where  dist - d <= k <= dist + d

The pruning rule follows from the triangle inequality: a word w under child k
has D(node, w) == k, so D(q, w) >= |dist - k|. If |dist - k| > d it cannot
match, so the whole subtree is skipped.
"""
import argparse
import json
import sys


def levenshtein(a, b, limit=None):
    """Edit distance (insert/delete/substitute, cost 1 each).

    Two-row DP, O(len(a)*len(b)) time, O(min) memory. If `limit` is given and
    the distance is certainly greater, returns limit + 1 early.
    """
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if limit is not None and len(a) - len(b) > limit:
        return limit + 1
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if limit is not None and min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


class BKTree:
    def __init__(self, words=(), distance=levenshtein):
        self._distance = distance
        self._root = None  # node = [word, {dist: child_node}]
        self._size = 0
        for w in words:
            self.add(w)

    def __len__(self):
        return self._size

    def add(self, word):
        """Insert word. Returns False if it was already present."""
        if self._root is None:
            self._root = [word, {}]
            self._size = 1
            return True
        node = self._root
        while True:
            d = self._distance(word, node[0])
            if d == 0:
                return False
            child = node[1].get(d)
            if child is None:
                node[1][d] = [word, {}]
                self._size += 1
                return True
            node = child

    def __contains__(self, word):
        return any(d == 0 for d, _ in self.search(word, 0))

    def search(self, query, max_dist, stats=None):
        """All (distance, word) with distance <= max_dist, sorted.

        If `stats` is a dict, stats['visited'] gets the number of distance
        computations done (compare with len(tree) for a linear scan).
        """
        if max_dist < 0:
            raise ValueError("max_dist must be >= 0")
        out = []
        visited = 0
        stack = [self._root] if self._root is not None else []
        while stack:
            word, children = stack.pop()
            visited += 1
            d = self._distance(query, word)
            if d <= max_dist:
                out.append((d, word))
            lo, hi = d - max_dist, d + max_dist
            for k, child in children.items():
                if lo <= k <= hi:
                    stack.append(child)
        if stats is not None:
            stats["visited"] = visited
        out.sort()
        return out

    def closest(self, query, n=1, max_dist=None):
        """Up to n nearest words. Widens radius until n found or max_dist hit."""
        if self._root is None or n <= 0:
            return []
        cap = max_dist if max_dist is not None else max(len(query), 1) + 64
        radius = 0
        while True:
            hits = self.search(query, radius)
            if len(hits) >= n or radius >= cap:
                return hits[:n]
            radius += 1

    def depth(self):
        best, stack = 0, ([(self._root, 1)] if self._root else [])
        while stack:
            (_, children), lvl = stack.pop()
            best = max(best, lvl)
            stack.extend((c, lvl + 1) for c in children.values())
        return best


def load_words(path):
    with open(path, encoding="utf-8") as fh:
        seen, words = set(), []
        for line in fh:
            w = line.strip()
            if w and not w.startswith("#") and w not in seen:
                seen.add(w)
                words.append(w)
    return words


def main(argv=None):
    p = argparse.ArgumentParser(description="Fuzzy word lookup with a BK-tree.")
    p.add_argument("wordlist", help="file with one word per line ('#' = comment)")
    p.add_argument("queries", nargs="+", help="words to look up")
    p.add_argument("-d", "--max-dist", type=int, default=2,
                   help="max edit distance (default 2)")
    p.add_argument("-n", "--limit", type=int, default=5,
                   help="max suggestions per query (default 5, 0 = all)")
    p.add_argument("-i", "--ignore-case", action="store_true",
                   help="lowercase words and queries")
    p.add_argument("--stats", action="store_true",
                   help="show distance computations vs. linear scan")
    p.add_argument("--json", action="store_true", help="JSON output")
    a = p.parse_args(argv)
    if a.max_dist < 0:
        p.error("--max-dist must be >= 0")

    try:
        words = load_words(a.wordlist)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.ignore_case:
        words = [w.lower() for w in words]
    tree = BKTree(words)

    results, missing = [], 0
    for q in a.queries:
        qq = q.lower() if a.ignore_case else q
        st = {}
        hits = tree.search(qq, a.max_dist, st)
        if a.limit:
            hits = hits[:a.limit]
        exact = bool(hits) and hits[0][0] == 0
        if not hits:
            missing += 1
        results.append({"query": q, "exact": exact, "visited": st["visited"],
                        "matches": [{"word": w, "distance": d} for d, w in hits]})

    if a.json:
        print(json.dumps({"words": len(tree), "depth": tree.depth(),
                          "max_dist": a.max_dist, "results": results}, indent=2))
    else:
        for r in results:
            tag = "ok" if r["exact"] else ("?" if r["matches"] else "no match")
            line = f"{r['query']}: {tag}"
            sugg = [f"{m['word']} ({m['distance']})" for m in r["matches"]
                    if m["distance"] > 0]
            if sugg and not r["exact"]:
                line += " -> " + ", ".join(sugg)
            if a.stats:
                pct = 100 * r["visited"] / max(len(tree), 1)
                line += f"  [{r['visited']}/{len(tree)} compared, {pct:.0f}%]"
            print(line)
    # exit 1 if any query had no match within max_dist (useful in scripts)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
