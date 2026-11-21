"""Skip list: a probabilistic ordered map with O(log n) expected operations.

Each node carries a tower of forward pointers. Level 0 is a plain sorted
linked list; each higher level skips over roughly 1/p of the nodes below it.
Search starts at the top level of the head and drops down whenever the next
key would overshoot. Every forward pointer also stores a *width* (how many
level-0 nodes it jumps), which makes rank / index-by-position O(log n) too.
"""

import random
import sys

__all__ = ["SkipList"]


class _Node:
    __slots__ = ("key", "value", "forward", "width")

    def __init__(self, key, value, level):
        self.key = key
        self.value = value
        self.forward = [None] * level
        self.width = [1] * level


class SkipList:
    def __init__(self, items=None, max_level=32, p=0.5, seed=None):
        if not 0 < p < 1:
            raise ValueError("p must be in (0, 1)")
        self._max = max_level
        self._p = p
        self._rng = random.Random(seed)
        self._head = _Node(None, None, max_level)
        self._level = 1
        self._len = 0
        for k, v in (items or {}).items() if isinstance(items, dict) else (items or []):
            self[k] = v

    # ---- internals -------------------------------------------------------
    def _random_level(self):
        lvl = 1
        while lvl < self._max and self._rng.random() < self._p:
            lvl += 1
        return lvl

    def _find_path(self, key):
        """Return (update, rank): last node before key on every level and the
        level-0 position (1-based, head=0) of each of those nodes."""
        update = [self._head] * self._max
        rank = [0] * self._max
        node = self._head
        pos = 0
        for i in range(self._level - 1, -1, -1):
            nxt = node.forward[i]
            while nxt is not None and nxt.key < key:
                pos += node.width[i]
                node = nxt
                nxt = node.forward[i]
            update[i] = node
            rank[i] = pos
        return update, rank

    # ---- mapping API -----------------------------------------------------
    def __len__(self):
        return self._len

    def __contains__(self, key):
        update, _ = self._find_path(key)
        nxt = update[0].forward[0]
        return nxt is not None and nxt.key == key

    def __getitem__(self, key):
        update, _ = self._find_path(key)
        nxt = update[0].forward[0]
        if nxt is None or nxt.key != key:
            raise KeyError(key)
        return nxt.value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        update, rank = self._find_path(key)
        nxt = update[0].forward[0]
        if nxt is not None and nxt.key == key:
            nxt.value = value
            return
        lvl = self._random_level()
        if lvl > self._level:
            for i in range(self._level, lvl):
                update[i] = self._head
                rank[i] = 0
                self._head.width[i] = self._len + 1  # spans to the end
            self._level = lvl
        node = _Node(key, value, lvl)
        pos = rank[0] + 1  # new node's 1-based position
        for i in range(lvl):
            prev = update[i]
            node.forward[i] = prev.forward[i]
            prev.forward[i] = node
            # prev's old width split into (pos - rank[i]) + remainder
            node.width[i] = prev.width[i] - (pos - rank[i]) + 1
            prev.width[i] = pos - rank[i]
        for i in range(lvl, self._level):
            update[i].width[i] += 1
        self._len += 1

    def __delitem__(self, key):
        update, _ = self._find_path(key)
        target = update[0].forward[0]
        if target is None or target.key != key:
            raise KeyError(key)
        for i in range(self._level):
            if update[i].forward[i] is target:
                update[i].width[i] += target.width[i] - 1
                update[i].forward[i] = target.forward[i]
            else:
                update[i].width[i] -= 1
        while self._level > 1 and self._head.forward[self._level - 1] is None:
            self._head.width[self._level - 1] = 1
            self._level -= 1
        self._len -= 1

    def pop(self, key, *default):
        try:
            v = self[key]
        except KeyError:
            if default:
                return default[0]
            raise
        del self[key]
        return v

    # ---- ordered API -----------------------------------------------------
    def __iter__(self):
        node = self._head.forward[0]
        while node is not None:
            yield node.key
            node = node.forward[0]

    def items(self):
        node = self._head.forward[0]
        while node is not None:
            yield node.key, node.value
            node = node.forward[0]

    def rank(self, key):
        """Number of keys strictly less than key."""
        _, rank = self._find_path(key)
        return rank[0]

    def at(self, index):
        """(key, value) at 0-based sorted position; negative indexes allowed."""
        if index < 0:
            index += self._len
        if not 0 <= index < self._len:
            raise IndexError("skip list index out of range")
        target = index + 1
        node, pos = self._head, 0
        for i in range(self._level - 1, -1, -1):
            while node.forward[i] is not None and pos + node.width[i] <= target:
                pos += node.width[i]
                node = node.forward[i]
        return node.key, node.value

    def range(self, lo=None, hi=None):
        """Yield (key, value) with lo <= key < hi (None = unbounded)."""
        if lo is None:
            node = self._head.forward[0]
        else:
            update, _ = self._find_path(lo)
            node = update[0].forward[0]
        while node is not None and (hi is None or node.key < hi):
            yield node.key, node.value
            node = node.forward[0]

    def floor(self, key):
        """Largest key <= key, or None."""
        update, _ = self._find_path(key)
        nxt = update[0].forward[0]
        if nxt is not None and nxt.key == key:
            return nxt.key
        return update[0].key  # head.key is None

    def ceiling(self, key):
        """Smallest key >= key, or None."""
        update, _ = self._find_path(key)
        nxt = update[0].forward[0]
        return None if nxt is None else nxt.key

    def check(self):
        """Verify ordering and width invariants; raise AssertionError if broken."""
        keys = list(self)
        assert keys == sorted(keys) and len(set(keys)) == len(keys), "order"
        assert len(keys) == self._len, "length"
        pos_of = {k: i + 1 for i, k in enumerate(keys)}
        for i in range(self._level):
            node, pos = self._head, 0
            while True:
                nxt = node.forward[i]
                end = self._len + 1 if nxt is None else pos_of[nxt.key]
                assert node.width[i] == end - pos, f"width level {i}"
                if nxt is None:
                    break
                node, pos = nxt, end
        return True

    def levels(self):
        """Text picture of the towers (for small lists)."""
        keys = list(self)
        col = {k: i for i, k in enumerate(keys)}
        w = max((len(str(k)) for k in keys), default=1)
        lines = []
        for i in range(self._level - 1, -1, -1):
            cells = ["-" * w] * len(keys)
            node = self._head.forward[i]
            while node is not None:
                cells[col[node.key]] = str(node.key).rjust(w)
                node = node.forward[i]
            lines.append(f"L{i}: " + " ".join(cells))
        return "\n".join(lines)


def main(argv=None):
    """Demo: python skiplist.py [--seed N] word ... -> sorted, ranks, towers."""
    args = list(sys.argv[1:] if argv is None else argv)
    seed = 1
    if args[:1] == ["--seed"]:
        seed = int(args[1])
        args = args[2:]
    if not args:
        print("usage: python skiplist.py [--seed N] KEY [KEY ...]", file=sys.stderr)
        return 2
    keys = [int(a) if a.lstrip("-").isdigit() else a for a in args]
    if len({type(k) for k in keys}) > 1:
        keys = [str(k) for k in keys]
    sl = SkipList(seed=seed)
    for k in keys:
        sl[k] = sl.get(k, 0) + 1
    sl.check()
    print(f"{len(sl)} unique keys, {sl._level} levels")
    print(sl.levels())
    print("counts:", ", ".join(f"{k}={v}" for k, v in sl.items()))
    print("median:", sl.at(len(sl) // 2)[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
