# log-cluster

Group log lines into templates. Each line has its variable parts masked (UUIDs, IPs, timestamps, hex, quoted strings, numbers). Lines that share a template form one cluster. Clusters are ranked by count, with example lines. It shows the shape of a noisy log in seconds.

Pure Python standard library. Single file, `log_cluster.py`.

## Usage

```
python log_cluster.py FILE [--top N] [--min N] [--examples N] [--json]
```

- `FILE` is a log file. Use `-` to read stdin.
- `--top N` shows at most N clusters (default 20).
- `--min N` hides clusters with fewer than N lines.
- `--examples N` shows N example lines per cluster (default 1, 0 hides them).
- `--json` prints a machine-readable report.

Exit codes: `0` success, `1` unreadable file, `2` bad arguments.

Masking runs in this order: UUID, ISO/space timestamp, time, IPv4 (with optional port), hex, quoted string, number. Whitespace is collapsed, so the same message with different spacing groups together.

Limitation: literal words are not masked. `/api/users` and `/api/users/42` form two clusters because the path is not a masked token.

### Example

`sample.log` has 10 lines (included in this folder).

```
$ python log_cluster.py sample.log --top 5
10 lines, 5 clusters shown
  count   share  template
      2   20.0%  <TS> ERROR upstream <IP> refused connection
                 L5: 2026-11-12T08:30:03.007Z ERROR upstream 10.0.0.12:5432 refused connection
      2   20.0%  <TS> INFO cache hit key <STR> ttl <NUM>
                 L7: 2026-11-12T08:30:04.512Z INFO  cache hit key "user:42" ttl 300
      1   10.0%  <TS> ERROR panic at <HEX> worker <NUM>
                 L10: 2026-11-12T08:30:05.330Z ERROR panic at 0xDEADBEEF worker 3
      1   10.0%  <TS> INFO cache miss key <STR> ttl <NUM>
                 L9: 2026-11-12T08:30:05.001Z INFO  cache miss key "user:99" ttl 300
      1   10.0%  <TS> INFO request <UUID> GET /api/orders <NUM> took <NUM> ms
                 L4: 2026-11-12T08:30:02.400Z INFO  request 0c9a1f2e-5d6b-4a1e-8f3c-7b2d9e4f1a6c GET /api/orders 500 t...
```

```
$ python log_cluster.py sample.log --top 2 --json
{
  "total_lines": 10,
  "clusters": 8,
  "shown": 2,
  "clusters_detail": [
    {
      "template": "<TS> ERROR upstream <IP> refused connection",
      "count": 2,
      "share": 20.0,
      "examples": [
        {
          "line": 5,
          "text": "2026-11-12T08:30:03.007Z ERROR upstream 10.0.0.12:5432 refused connection"
        }
      ]
    },
    {
      "template": "<TS> INFO cache hit key <STR> ttl <NUM>",
      "count": 2,
      "share": 20.0,
      "examples": [
        {
          "line": 7,
          "text": "2026-11-12T08:30:04.512Z INFO  cache hit key \"user:42\" ttl 300"
        }
      ]
    }
  ]
}
```

Missing file:

```
$ python log_cluster.py nope.log
log-cluster: cannot read nope.log: No such file or directory
$ echo $?
1
```

## Tests

```
$ python -m unittest
...........................
----------------------------------------------------------------------
Ran 27 tests in 0.046s

OK
```

Tests cover each mask, whitespace collapsing, grouping and example line numbers, ranking and filters, JSON shares, and CLI exit codes.
