# dice-prob

Exact probability calculator for tabletop dice notation. Every probability is a
`fractions.Fraction`, so results are exact (no floating-point drift). Python
standard library only.

## Supported notation

- `NdS`: sum of N dice with S sides (`3d6`, `d20`; N defaults to 1)
- `d%`: percentile die (1..100)
- `NdF`: Fudge/FATE dice (-1, 0, +1)
- `kh M` / `k M`: keep highest M (`2d20kh1` = advantage)
- `kl M`: keep lowest M (`2d20kl1` = disadvantage)
- `dl M` / `d M`: drop lowest M (`4d6dl1` = D&D stat roll)
- `dh M`: drop highest M
- `+`, `-`, integer constants: `1d8+1d6+3`, `1d4-1d4`

## How it works

- Plain sums use discrete convolution, with exponentiation by squaring
  (`100d6` needs about 7 convolutions, not 100).
- Keep/drop terms are enumerated directly when there are at most 2,000,000
  outcomes. Larger pools such as `10d20kh3` use an order-statistic DP instead.
  The DP walks face values from best to worst. At each value it picks how many
  of the remaining dice show it, weighted by `C(left, c)`, and keeps as many as
  still needed. Tests cross-check the DP against enumeration.

## Usage

```
python dice_prob.py EXPR [-p QUERY] [--no-hist] [--json]
```

`QUERY` is one of `>=N`, `>N`, `<=N`, `<N`, `=N`. Exit code is 0 on success and
2 on a bad expression or query.

```
$ python dice_prob.py 2d6 -p ">=10"
2d6: range 2..12, mean 7.0000 (7), stdev 2.4152, median 7, mode 7
P(X >= 10) = 1/6 = 16.6667%
 2   2.78% #######
 3   5.56% #############
 4   8.33% ####################
 5  11.11% ###########################
 6  13.89% #################################
 7  16.67% ########################################
 8  13.89% #################################
 9  11.11% ###########################
10   8.33% ####################
11   5.56% #############
12   2.78% #######

$ python dice_prob.py 4d6dl1 -p ">=15" --no-hist
4d6dl1: range 3..18, mean 12.2446 (15869/1296), stdev 2.8468, median 12, mode 13
P(X >= 15) = 25/108 = 23.1481%

$ python dice_prob.py 2d20kh1+5 -p ">=20" --no-hist
2d20kh1+5: range 6..25, mean 18.8250 (753/40), stdev 4.7111, median 20, mode 25
P(X >= 20) = 51/100 = 51.0000%

$ python dice_prob.py 10d20kh3 -p ">=50" --no-hist
10d20kh3: range 3..60, mean 50.5492 (2588121164321/51200000000), stdev 5.6875, median 51, mode 54
P(X >= 50) = 804068875143/1280000000000 = 62.8179%

$ python dice_prob.py 4dF
4dF: range -4..4, mean 0.0000 (0), stdev 1.6330, median 0, mode 0
-4   1.23% ##
-3   4.94% ########
-2  12.35% #####################
-1  19.75% ##################################
 0  23.46% ########################################
 1  19.75% ##################################
 2  12.35% #####################
 3   4.94% ########
 4   1.23% ##

$ python dice_prob.py d4 --json -p "=2"
{
  "expr": "d4",
  "stats": {
    "min": 1,
    "max": 4,
    "mean": "5/2",
    "variance": "5/4",
    "stdev": 1.118033988749895,
    "mode": 1,
    "median": 2
  },
  "distribution": {
    "1": "1/4",
    "2": "1/4",
    "3": "1/4",
    "4": "1/4"
  },
  "query": {
    "op": "=",
    "target": 2,
    "p": "1/4",
    "float": 0.25
  }
}

$ python dice_prob.py 2q6; echo "exit $?"
error: expected + or - at position 1: 'q6'
exit 2
```

When several values tie for most likely, `mode` reports the smallest one.

## Tests

```
python -m unittest -v
```

16 tests cover the following: known exact values (advantage, 4d6 drop lowest,
4dF), mean and variance, DP vs enumeration agreement, large pools, queries, CLI
text and JSON output, and error exit codes.
