"""Bloom filter: a space-efficient probabilistic set.

A Bloom filter answers "is x in the set?" with either
  * "definitely not"  (no false negatives), or
  * "probably yes"    (false positives possible, at a tunable rate).

It is a bit array of m bits plus k hash functions. add(x) sets the k bits
h_1(x)..h_k(x); contains(x) checks that all k bits are set.

Sizing for n expected items and target false-positive rate p:
    m = -n * ln(p) / (ln 2)^2
    k = (m / n) * ln 2
Estimated false-positive rate after inserting n items:
    p ~= (1 - e^(-k*n/m))^k

Instead of k independent hash functions we use double hashing
(Kirsch & Mitzenmacher, 2006): g_i(x) = h1(x) + i*h2(x) mod m, where h1 and
h2 come from one SHA-256 digest. This keeps the same asymptotic FP rate.
"""

import argparse
import base64
import hashlib
import json
import math
import sys


class BloomFilter:
    def __init__(self, m, k):
        if m < 1 or k < 1:
            raise ValueError("m and k must be >= 1")
        self.m = int(m)
        self.k = int(k)
        self.bits = bytearray((self.m + 7) // 8)
        self.count = 0

    @classmethod
    def for_capacity(cls, n, p=0.01):
        """Create a filter sized for n items at false-positive rate p."""
        if n < 1:
            raise ValueError("n must be >= 1")
        if not 0 < p < 1:
            raise ValueError("p must be between 0 and 1")
        m = math.ceil(-n * math.log(p) / (math.log(2) ** 2))
        k = max(1, round(m / n * math.log(2)))
        return cls(m, k)

    def _indexes(self, item):
        data = item.encode("utf-8") if isinstance(item, str) else bytes(item)
        digest = hashlib.sha256(data).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:16], "big") | 1  # odd => never zero
        return [(h1 + i * h2) % self.m for i in range(self.k)]

    def add(self, item):
        for idx in self._indexes(item):
            self.bits[idx >> 3] |= 1 << (idx & 7)
        self.count += 1

    def __contains__(self, item):
        return all(self.bits[idx >> 3] & (1 << (idx & 7))
                   for idx in self._indexes(item))

    def bits_set(self):
        return sum(bin(b).count("1") for b in self.bits)

    def estimated_fp_rate(self):
        """Theoretical FP rate given the number of items added."""
        return (1 - math.exp(-self.k * self.count / self.m)) ** self.k

    def union(self, other):
        if (self.m, self.k) != (other.m, other.k):
            raise ValueError("filters must share m and k")
        out = BloomFilter(self.m, self.k)
        out.bits = bytearray(a | b for a, b in zip(self.bits, other.bits))
        out.count = self.count + other.count
        return out

    def to_dict(self):
        return {"m": self.m, "k": self.k, "count": self.count,
                "bits": base64.b64encode(bytes(self.bits)).decode("ascii")}

    @classmethod
    def from_dict(cls, d):
        bf = cls(d["m"], d["k"])
        bits = base64.b64decode(d["bits"])
        if len(bits) != len(bf.bits):
            raise ValueError("bit array length does not match m")
        bf.bits = bytearray(bits)
        bf.count = d.get("count", 0)
        return bf

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def _read_lines(path):
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        return [ln.rstrip("\r\n") for ln in stream if ln.strip()]
    finally:
        if stream is not sys.stdin:
            stream.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build and query Bloom filters.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a filter from a word list")
    b.add_argument("input", help="file with one item per line ('-' = stdin)")
    b.add_argument("-o", "--output", required=True, help="filter JSON path")
    b.add_argument("-p", "--fp-rate", type=float, default=0.01)
    b.add_argument("-n", "--capacity", type=int,
                   help="expected items (default: number of input lines)")

    q = sub.add_parser("query", help="test items against a filter")
    q.add_argument("filter")
    q.add_argument("items", nargs="+")

    s = sub.add_parser("info", help="show filter statistics")
    s.add_argument("filter")

    sz = sub.add_parser("size", help="compute m and k for n items at rate p")
    sz.add_argument("n", type=int)
    sz.add_argument("p", type=float)

    args = ap.parse_args(argv)

    if args.cmd == "build":
        items = _read_lines(args.input)
        bf = BloomFilter.for_capacity(args.capacity or max(1, len(items)),
                                      args.fp_rate)
        for it in items:
            bf.add(it)
        bf.save(args.output)
        print(f"built {args.output}: {bf.count} items, m={bf.m} bits "
              f"({len(bf.bits)} bytes), k={bf.k}")
    elif args.cmd == "query":
        bf = BloomFilter.load(args.filter)
        missing = 0
        for it in args.items:
            hit = it in bf
            missing += not hit
            print(f"{it}\t{'probably present' if hit else 'definitely absent'}")
        return 1 if missing else 0
    elif args.cmd == "info":
        bf = BloomFilter.load(args.filter)
        print(f"m (bits):        {bf.m}")
        print(f"k (hashes):      {bf.k}")
        print(f"items added:     {bf.count}")
        print(f"bits set:        {bf.bits_set()} "
              f"({bf.bits_set() / bf.m:.1%})")
        print(f"est. FP rate:    {bf.estimated_fp_rate():.4%}")
    elif args.cmd == "size":
        bf = BloomFilter.for_capacity(args.n, args.p)
        print(f"n={args.n} p={args.p}: m={bf.m} bits "
              f"({math.ceil(bf.m / 8)} bytes), k={bf.k}, "
              f"{bf.m / args.n:.2f} bits/item")
    return 0


if __name__ == "__main__":
    sys.exit(main())
