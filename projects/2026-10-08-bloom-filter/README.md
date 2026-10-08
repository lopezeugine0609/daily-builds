# bloom-filter

A Bloom filter in pure Python (standard library only), with a small CLI to build, query, and inspect filters saved as JSON.

## What it is

A Bloom filter is a space-efficient probabilistic set. A membership query returns one of two answers:

- **definitely absent**: false negatives never happen.
- **probably present**: false positives can happen, at a rate you choose.

The filter is a bit array of `m` bits plus `k` hash functions. `add(x)` sets the `k` bits at positions `h_1(x)..h_k(x)`. A query checks that all `k` bits are set.

For `n` expected items and a target false-positive rate `p`:

```
m = -n * ln(p) / (ln 2)^2      # bits
k = (m / n) * ln 2             # hash functions
p_est ≈ (1 - e^(-k*n/m))^k     # FP rate after n inserts
```

The filter does not use `k` independent hashes. It uses **double hashing** (Kirsch & Mitzenmacher): `g_i(x) = h1(x) + i*h2(x) mod m`. Both `h1` and `h2` come from a single SHA-256 digest. `h2` is forced odd so it is never zero. This approach gives the same asymptotic FP rate for much less hashing work.

At 1% FP, a Bloom filter needs about 9.6 bits per item, whatever the item size.

## Library usage

```python
from bloom import BloomFilter

bf = BloomFilter.for_capacity(1000, p=0.01)   # m=9586, k=7
bf.add("alice@example.com")
"alice@example.com" in bf   # True
"bob@example.com" in bf     # False (almost certainly)
bf.estimated_fp_rate()
bf.union(other)             # OR of two filters that share m and k
bf.save("f.json"); BloomFilter.load("f.json")
```

## CLI usage

```
python bloom.py size <n> <p>                  # compute m and k
python bloom.py build <file|-> -o out.json [-p 0.01] [-n capacity]
python bloom.py query out.json item1 item2 …  # exit 1 if any item is absent
python bloom.py info out.json
```

Real output:

```
$ python bloom.py size 1000000 0.001
n=1000000 p=0.001: m=14377588 bits (1797199 bytes), k=10, 14.38 bits/item

$ printf 'apple\nbanana\ncherry\ndate\nelderberry\n' > fruits.txt
$ python bloom.py build fruits.txt -o fruits.json -p 0.01
built fruits.json: 5 items, m=48 bits (6 bytes), k=7

$ python bloom.py query fruits.json apple cherry mango
apple	probably present
cherry	probably present
mango	definitely absent

$ python bloom.py info fruits.json
m (bits):        48
k (hashes):      7
items added:     5
bits set:        30 (62.5%)
est. FP rate:    0.9965%
```

## Tests

```
python -m unittest -v
```

There are 10 tests. They cover the sizing formula, absence of false negatives, measured FP rate against the target (5,000 items, 20,000 disjoint probes), union, JSON round-trip, invalid arguments, and the CLI.
