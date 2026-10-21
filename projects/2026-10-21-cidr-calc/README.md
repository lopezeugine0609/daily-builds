# cidr-calc

IPv4 subnet calculator CLI in plain Node.js (no dependencies).

- `info` — network, broadcast, netmask, wildcard, host range, usable hosts, address type (private/public/loopback/CGNAT/...). `/31` and `/32` follow RFC 3021 (no reserved addresses).
- `contains` — check whether an IP or CIDR lies inside another CIDR; exit code `0` yes, `1` no (handy in shell scripts).
- `split` — carve a network into equal subnets of a longer prefix.
- `summarize` — merge overlapping/adjacent CIDRs, bare IPs and `a-b` ranges into the minimal CIDR list.

Add `--json` to any command for machine-readable output. Invalid input exits `2`.

## How summarize works

Inputs become inclusive `[start, end]` integer ranges, get sorted, and are merged when they overlap or touch (`next.start <= prev.end + 1`). Each merged range is then covered greedily: from the current address, take the largest power-of-two block that is both aligned (`start % size == 0`) and does not overshoot `end`. That greedy choice is optimal, so the output is the smallest possible CIDR list.

## Usage

```
$ node cidr.js info 192.168.1.77/24
cidr            192.168.1.0/24
address         192.168.1.77
netmask         255.255.255.0
wildcard        0.0.0.255
network         192.168.1.0
broadcast       192.168.1.255
firstHost       192.168.1.1
lastHost        192.168.1.254
totalAddresses  256
usableHosts     254
type            private (RFC 1918)

$ node cidr.js contains 10.0.0.0/8 10.20.30.40; echo "exit $?"
yes: 10.20.30.40 is in 10.0.0.0/8
exit 0

$ node cidr.js contains 10.0.0.0/8 11.0.0.1; echo "exit $?"
no: 11.0.0.1 is not in 10.0.0.0/8
exit 1

$ node cidr.js split 192.168.0.0/24 26
192.168.0.0/26
192.168.0.64/26
192.168.0.128/26
192.168.0.192/26

$ node cidr.js summarize 10.0.1.0/24 10.0.0.0/24 10.0.2.0/25 10.0.0.1-10.0.0.6
10.0.0.0/23
10.0.2.0/25

$ node cidr.js summarize 10.0.0.1-10.0.0.6
10.0.0.1/32
10.0.0.2/31
10.0.0.4/31
10.0.0.6/32

$ node cidr.js info 10.1.2.3/8 --json
{
  "cidr": "10.0.0.0/8",
  "address": "10.1.2.3",
  "netmask": "255.0.0.0",
  "wildcard": "0.255.255.255",
  "network": "10.0.0.0",
  "broadcast": "10.255.255.255",
  "firstHost": "10.0.0.1",
  "lastHost": "10.255.255.254",
  "totalAddresses": 16777216,
  "usableHosts": 16777214,
  "type": "private (RFC 1918)"
}

$ node cidr.js info 300.1.1.1; echo "exit $?"
error: invalid IPv4 address: 300.1.1.1
exit 2
```

Also usable as a module: `const { info, contains, split, summarize } = require('./cidr.js')`.

## Tests

```
node --test
```

9 tests: parsing/validation, /0 /31 /32 edge cases, contains, split limits, minimal range covering, summarize merging, CLI exit codes.
