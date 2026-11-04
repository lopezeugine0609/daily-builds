# cache-sim

Replay an access trace against four cache replacement policies and compare hit rates:

- **LRU**: evict the least recently used key
- **FIFO**: evict the oldest inserted key (hits do not refresh)
- **LFU**: evict the least frequently used key, ties broken by least recent use
- **OPT**: Belady's optimal. Evicts the key whose next use is farthest away. It needs the whole trace, so it is offline, but it gives an upper bound for any policy.

Pure Python standard library. Single file, `cache_sim.py`.

## Usage

```
python cache_sim.py TRACE [-c 1,2,4,8,16] [-p all|lru,fifo,lfu,opt] [--json]
```

- `TRACE` is a whitespace-separated list of keys. Lines starting with `#` are comments. Use `-` to read stdin.
- `-c` takes a comma-separated list of cache sizes.
- `-p` selects policies.
- `--json` prints machine-readable output.

Exit codes: `0` success, `1` unreadable trace file, `2` bad arguments.

### Example

`trace.txt`:

```
# sample access trace
A B C A B D A D E A
B C A B D C
```

```
$ python cache_sim.py trace.txt -c 2,3,4
trace: 16 accesses, 5 distinct keys
capacity      lru     fifo      lfu      opt
       2     6.2%    12.5%    12.5%    37.5%
       3    43.8%    37.5%    43.8%    56.2%
       4    56.2%    43.8%    62.5%    62.5%
```

```
$ python cache_sim.py trace.txt -c 3 -p lru,opt --json
{
  "accesses": 16,
  "distinct": 5,
  "results": [
    {
      "policy": "lru",
      "capacity": 3,
      "hits": 7,
      "misses": 9,
      "hit_rate": 0.4375
    },
    {
      "policy": "opt",
      "capacity": 3,
      "hits": 9,
      "misses": 7,
      "hit_rate": 0.5625
    }
  ]
}
```

OPT is never below the other policies in the table, which is the expected bound.

## How OPT works

Scan the trace backwards once to record each access's next-use index. Forward pass: on a miss with a full cache, evict the resident key with the largest next-use index. Keys never used again have index `inf` and go first.

## Tests

Run from the project folder:

```
python -m unittest -v
```

The suite (22 tests) covers hand-traced LRU/FIFO/LFU cases, the FIFO Belady anomaly (3 frames: 3 hits, 4 frames: 2 hits on the textbook sequence), an OPT check against exhaustive search over random small traces, the OPT-is-an-upper-bound property, CLI output, JSON, stdin, and error exit codes.

Output of the last test run:

```
......................
----------------------------------------------------------------------
Ran 22 tests in 0.047s

OK
```
