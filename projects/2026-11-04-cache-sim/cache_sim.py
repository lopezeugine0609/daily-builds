#!/usr/bin/env python
"""cache-sim: replay an access trace against cache replacement policies.

Policies:
  lru   evict the least recently used key
  fifo  evict the oldest inserted key (hits do not refresh)
  lfu   evict the least frequently used key, ties broken by least recent use
  opt   Belady's optimal: evict the key whose next use is farthest away
        (offline, needs the whole trace; an upper bound for any policy)
"""
import argparse
import json
import sys
from collections import OrderedDict, deque

POLICIES = ("lru", "fifo", "lfu", "opt")
INF = float("inf")


class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()

    def access(self, key):
        if key in self.data:
            self.data.move_to_end(key)
            return True
        if len(self.data) >= self.capacity:
            self.data.popitem(last=False)
        self.data[key] = None
        return False


class FIFO:
    def __init__(self, capacity):
        self.capacity = capacity
        self.order = deque()
        self.members = set()

    def access(self, key):
        if key in self.members:
            return True
        if len(self.members) >= self.capacity:
            self.members.discard(self.order.popleft())
        self.order.append(key)
        self.members.add(key)
        return False


class LFU:
    def __init__(self, capacity):
        self.capacity = capacity
        self.freq = {}
        self.last = {}
        self.tick = 0

    def access(self, key):
        self.tick += 1
        if key in self.freq:
            self.freq[key] += 1
            self.last[key] = self.tick
            return True
        if len(self.freq) >= self.capacity:
            victim = min(self.freq, key=lambda k: (self.freq[k], self.last[k]))
            del self.freq[victim]
            del self.last[victim]
        self.freq[key] = 1
        self.last[key] = self.tick
        return False


CLASSES = {"lru": LRU, "fifo": FIFO, "lfu": LFU}


def simulate_opt(trace, capacity):
    """Belady's OPT. Returns hit count."""
    n = len(trace)
    next_use = [INF] * n
    seen = {}
    for i in range(n - 1, -1, -1):
        next_use[i] = seen.get(trace[i], INF)
        seen[trace[i]] = i

    cache = {}  # key -> index of its next use
    hits = 0
    for i, key in enumerate(trace):
        if key in cache:
            hits += 1
        elif len(cache) >= capacity:
            victim = max(cache, key=lambda k: cache[k])
            del cache[victim]
        cache[key] = next_use[i]
    return hits


def simulate(trace, capacity, policy):
    """Replay trace; return dict with hits, misses, hit_rate."""
    if capacity < 1:
        raise ValueError("capacity must be >= 1")
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    if policy == "opt":
        hits = simulate_opt(trace, capacity)
    else:
        cache = CLASSES[policy](capacity)
        hits = sum(1 for key in trace if cache.access(key))
    total = len(trace)
    misses = total - hits
    return {
        "policy": policy,
        "capacity": capacity,
        "hits": hits,
        "misses": misses,
        "hit_rate": hits / total if total else 0.0,
    }


def parse_trace(text):
    """Keys are whitespace-separated tokens. Lines starting with # are comments."""
    keys = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.extend(stripped.split())
    return keys


def parse_list(value, cast, name):
    try:
        items = [cast(part) for part in value.split(",") if part.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"bad {name} list: {value!r}")
    if not items:
        raise argparse.ArgumentTypeError(f"empty {name} list")
    return items


def build_parser():
    p = argparse.ArgumentParser(
        prog="cache-sim",
        description="Replay an access trace against LRU, FIFO, LFU and OPT caches.",
    )
    p.add_argument("trace", help="trace file, or - for stdin")
    p.add_argument(
        "-c", "--capacity", default="1,2,4,8,16",
        help="comma-separated cache sizes (default: 1,2,4,8,16)",
    )
    p.add_argument(
        "-p", "--policy", default="all",
        help="comma-separated subset of lru,fifo,lfu,opt (default: all)",
    )
    p.add_argument("--json", action="store_true", help="print JSON")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        capacities = parse_list(args.capacity, int, "capacity")
        if args.policy == "all":
            policies = list(POLICIES)
        else:
            policies = parse_list(args.policy, str, "policy")
            bad = [p for p in policies if p not in POLICIES]
            if bad:
                parser.error(f"unknown policy: {', '.join(bad)}")
        if any(c < 1 for c in capacities):
            parser.error("capacity must be >= 1")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    try:
        if args.trace == "-":
            text = sys.stdin.read()
        else:
            with open(args.trace, encoding="utf-8") as fh:
                text = fh.read()
    except OSError as exc:
        print(f"cache-sim: {exc}", file=sys.stderr)
        return 1

    trace = parse_trace(text)
    distinct = len(set(trace))
    results = [simulate(trace, c, p) for c in capacities for p in policies]

    if args.json:
        out = {"accesses": len(trace), "distinct": distinct, "results": results}
        print(json.dumps(out, indent=2))
        return 0

    print(f"trace: {len(trace)} accesses, {distinct} distinct keys")
    print(f"{'capacity':>8}  " + "  ".join(f"{p:>7}" for p in policies))
    lookup = {(r["capacity"], r["policy"]): r["hit_rate"] for r in results}
    for c in capacities:
        cells = "  ".join(f"{lookup[(c, p)] * 100:6.1f}%" for p in policies)
        print(f"{c:>8}  {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
